// ── Karwan-e-Khizr: Transit Service ──
// Abstraction layer between UI and data sources (FastAPI <-> mock fallback).
//
// Data flow:
//   UI -> Hooks -> TransitService -> API Client -> FastAPI -> PostgreSQL/PostGIS
//                              \\-> Mock Data (when backend is unavailable)
//
// The service attempts real API calls first and falls back to mock data when:
//   - The backend is unreachable (NetworkError, TimeoutError)
//   - The server returns an error (5xx)
//
// Endpoints and request/response shapes here match the real backend exactly
// (see backend/app/api/*.py, backend/app/*/router.py, backend/app/*/schemas.py).
// Raw wire shapes live in `../types/api`; this file's job is to call the real
// endpoints and adapt their responses into the UI-facing view-model types in
// `../types` that screens/components consume.

import type {
  Bus,
  Stop,
  TransitRoute,
  Journey,
  JourneySegment,
  SearchResult,
} from '../types';
import type {
  ApiRouteListResponse,
  ApiRoute,
  ApiStopListResponse,
  ApiStop,
  ApiVehiclePositionResponse,
  ApiVehiclePosition,
  ApiVehicleETA,
  ApiJourneySearchResponse,
  ApiJourney,
  ApiLeg,
  ApiLocationResolved,
  JourneyObjective,
  ApiRegisterResponse,
  ApiLoginResponse,
  ApiUserPublic,
  ApiFareQuote,
  ApiTicketResponse,
  ApiTicketListResponse,
  ApiValidationResult,
  ApiConverseResponse,
  ApiAmbiguousLocationError,
} from '../types/api';
import { apiClient, authHeaders } from './api-client';
import { ApiError, NetworkError, TimeoutError } from './api-client';
import { getConfig } from './config';

// Mock data imports (fallback)
import { mockBuses } from '../mocks/buses';
import { mockStops } from '../mocks/stops';
import { mockRoutes } from '../mocks/routes';
import { mockJourneys } from '../mocks/journeys';
import { mockSearchResults } from '../mocks/search';

// ── Helpers ──

/** Returns true when the error indicates the backend is unavailable. */
function isBackendUnavailable(error: unknown): boolean {
  if (error instanceof NetworkError) return true;
  if (error instanceof TimeoutError) return true;
  if (error instanceof ApiError) {
    // 5xx = server error. 404 is a legitimate "not found" for detail
    // endpoints now that the real routes/stops/vehicles endpoints exist,
    // so it's handled by each call site rather than treated as "backend
    // is down".
    return error.status >= 500;
  }
  return false;
}

/** Log a fallback event for developer visibility. */
function logFallback(operation: string, reason: unknown): void {
  if (typeof console !== 'undefined') {
    console.warn(
      `[TransitService] "${operation}" fell back to mock data:`,
      reason instanceof Error ? reason.message : reason,
    );
  }
}

// ── Simulated latency for mock data ──

function withMockDelay<T>(data: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), 150));
}

// ── Errors specific to journey search ──

/** Thrown when the backend can't disambiguate a typed origin/destination. */
export class AmbiguousLocationError extends Error {
  constructor(
    public field: 'origin' | 'destination',
    public candidates: ApiLocationResolved[],
  ) {
    super(`"${field}" is ambiguous`);
    this.name = 'AmbiguousLocationError';
  }
}

/** Thrown when no route could be found between two resolved locations. */
export class NoRouteFoundError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NoRouteFoundError';
  }
}

function parseJourneySearchError(error: ApiError): never {
  const body = error.body as { detail?: ApiAmbiguousLocationError | { error: string; message: string } } | undefined;
  const detail = body?.detail;
  if (detail && typeof detail === 'object' && 'error' in detail) {
    if (detail.error === 'ambiguous_origin' || detail.error === 'ambiguous_destination') {
      const amb = detail as ApiAmbiguousLocationError;
      throw new AmbiguousLocationError(
        amb.error === 'ambiguous_origin' ? 'origin' : 'destination',
        amb.candidates,
      );
    }
    if (detail.error === 'no_route_found') {
      throw new NoRouteFoundError((detail as { message: string }).message ?? 'No route found');
    }
  }
  throw error;
}

// ── Adapters: API shape -> UI view-model ──

function adaptRoute(r: ApiRoute): TransitRoute {
  return {
    id: String(r.id),
    name: r.long_name ?? r.short_name,
    shortName: r.short_name,
    color: r.color ?? '#6B7280',
    type: r.route_type,
    stops: [],
    polyline: [],
    // frequency/operatingHours intentionally omitted: not exposed by the
    // API yet (the underlying data exists in the seed dataset but hasn't
    // been modelled into the routes table).
  };
}

function adaptStop(s: ApiStop): Stop {
  return {
    id: String(s.id),
    name: s.name,
    latitude: s.lat,
    longitude: s.lon,
    routeIds: [],
    // The API doesn't classify stops (bus stop vs. metro station vs.
    // terminal) today, so this is a safe default rather than real data.
    type: 'bus-stop',
  };
}

function adaptVehicle(
  v: ApiVehiclePosition,
  routesById: Map<number, TransitRoute>,
  stopsById: Map<number, Stop>,
): Bus {
  const route = routesById.get(v.route_id);
  const nextStop = v.next_stop_id != null ? stopsById.get(v.next_stop_id) : undefined;
  return {
    id: String(v.id),
    routeId: String(v.route_id),
    routeName: route?.name ?? `Route ${v.route_id}`,
    routeColor: route?.color ?? '#6B7280',
    latitude: v.latitude,
    longitude: v.longitude,
    heading: v.bearing ?? 0,
    speed: v.speed != null ? Math.round(v.speed * 3.6) : 0, // m/s -> km/h
    status: v.status,
    nextStopId: v.next_stop_id != null ? String(v.next_stop_id) : null,
    nextStopName: nextStop?.name ?? null,
    eta: v.eta_seconds != null ? Math.round(v.eta_seconds / 60) : null,
    vehicleNumber: v.label,
  };
}

/** Build a stable-enough id for an ephemeral (non-persisted) search result journey. */
function journeyId(index: number, j: ApiJourney): string {
  return `journey-${index}-${j.legs.length}-${j.total_duration_s}`;
}

function adaptLeg(
  leg: ApiLeg,
  index: number,
  legs: ApiLeg[],
  routesById: Map<number, TransitRoute>,
  stopsById: Map<number, Stop>,
  originResolved: ApiLocationResolved,
  destinationResolved: ApiLocationResolved,
): JourneySegment {
  const isFirst = index === 0;
  const isLast = index === legs.length - 1;

  if (leg.type === 'walk') {
    const fromName = isFirst ? originResolved.name : (stopsById.get(leg.start_stop_id)?.name ?? `Stop ${leg.start_stop_id}`);
    const toName = isLast ? destinationResolved.name : (stopsById.get(leg.end_stop_id)?.name ?? `Stop ${leg.end_stop_id}`);
    return {
      type: 'walk',
      duration: Math.round(leg.duration_s / 60),
      distance: Math.round(leg.distance_m ?? 0),
      from: { name: fromName, latitude: leg.start_lat, longitude: leg.start_lon },
      to: { name: toName, latitude: leg.end_lat, longitude: leg.end_lon },
    };
  }

  // "ride" leg
  const route = leg.route_id != null ? routesById.get(leg.route_id) : undefined;
  const fromStop = stopsById.get(leg.start_stop_id);
  const toStop = stopsById.get(leg.end_stop_id);
  const fromName = fromStop?.name ?? (isFirst ? originResolved.name : `Stop ${leg.start_stop_id}`);
  const toName = toStop?.name ?? (isLast ? destinationResolved.name : `Stop ${leg.end_stop_id}`);

  return {
    type: route?.type ?? 'bus',
    routeId: leg.route_id != null ? String(leg.route_id) : '',
    routeName: route?.name ?? (leg.route_id != null ? `Route ${leg.route_id}` : 'Unknown route'),
    routeShortName: route?.shortName ?? (leg.route_id != null ? String(leg.route_id) : '?'),
    routeColor: route?.color ?? '#6B7280',
    fromStop: { id: fromStop ? fromStop.id : String(leg.start_stop_id), name: fromName, latitude: leg.start_lat, longitude: leg.start_lon },
    toStop: { id: toStop ? toStop.id : String(leg.end_stop_id), name: toName, latitude: leg.end_lat, longitude: leg.end_lon },
    duration: Math.round(leg.duration_s / 60),
    // Per-leg intermediate stop counts aren't returned by the API.
    stops: undefined,
    direction: `toward ${toName}`,
  };
}

function adaptJourney(
  j: ApiJourney,
  index: number,
  routesById: Map<number, TransitRoute>,
  stopsById: Map<number, Stop>,
  originResolved: ApiLocationResolved,
  destinationResolved: ApiLocationResolved,
): Journey {
  const fare = j.fare;
  return {
    id: journeyId(index, j),
    segments: j.legs.map((leg, i) => adaptLeg(leg, i, j.legs, routesById, stopsById, originResolved, destinationResolved)),
    totalDuration: Math.round(j.total_duration_s / 60),
    totalWalkDistance: Math.round(j.total_walk_m),
    transferCount: j.transfer_count,
    fare: fare?.total ?? 0,
    fareLabel: fare ? `${fare.currency} ${fare.total.toFixed(2)}` : 'Fare unavailable',
    // The backend ranks results for the requested objective but doesn't
    // tag individual journeys; the top result is a reasonable stand-in
    // for "recommended".
    tag: index === 0 ? 'recommended' : undefined,
  };
}

// ── Service class ──

export interface JourneySearchOptions {
  objective?: JourneyObjective;
  maxWalkM?: number;
  maxTransfers?: number;
  departureTime?: string;
}

class TransitService {
  // ── Routes ──

  async getRoutes(signal?: AbortSignal): Promise<TransitRoute[]> {
    if (getConfig().useMockData) return withMockDelay(mockRoutes);
    try {
      const res = await apiClient.get<ApiRouteListResponse>('/transit/routes', { limit: 500 }, signal);
      return res.routes.map(adaptRoute);
    } catch (error) {
      if (isBackendUnavailable(error)) {
        logFallback('getRoutes', error);
        return mockRoutes;
      }
      throw error;
    }
  }

  async getRoute(id: string, signal?: AbortSignal): Promise<TransitRoute | null> {
    if (getConfig().useMockData) {
      return withMockDelay(mockRoutes.find((r) => r.id === id) ?? null);
    }
    try {
      const route = await apiClient.get<ApiRoute>(`/transit/routes/${encodeURIComponent(id)}`, undefined, signal);
      return adaptRoute(route);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      if (isBackendUnavailable(error)) {
        logFallback('getRoute', error);
        return mockRoutes.find((r) => r.id === id) ?? null;
      }
      throw error;
    }
  }

  // ── Stops ──

  async getStops(signal?: AbortSignal): Promise<Stop[]> {
    if (getConfig().useMockData) return withMockDelay(mockStops);
    try {
      const res = await apiClient.get<ApiStopListResponse>('/transit/stops', { limit: 1000 }, signal);
      return res.stops.map(adaptStop);
    } catch (error) {
      if (isBackendUnavailable(error)) {
        logFallback('getStops', error);
        return mockStops;
      }
      throw error;
    }
  }

  async getStop(id: string, signal?: AbortSignal): Promise<Stop | null> {
    if (getConfig().useMockData) {
      return withMockDelay(mockStops.find((s) => s.id === id) ?? null);
    }
    try {
      const stop = await apiClient.get<ApiStop>(`/transit/stops/${encodeURIComponent(id)}`, undefined, signal);
      return adaptStop(stop);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      if (isBackendUnavailable(error)) {
        logFallback('getStop', error);
        return mockStops.find((s) => s.id === id) ?? null;
      }
      throw error;
    }
  }

  // ── Vehicles (Buses) ──
  // NOTE: the real endpoint returns bare numeric route_id/next_stop_id, so
  // callers should pass already-fetched routes/stops (e.g. from
  // useTransitData) so vehicles can be enriched with names/colors. When
  // omitted, vehicles fall back to generic "Route <id>" labels.

  async getVehicles(
    signal?: AbortSignal,
    routes: TransitRoute[] = [],
    stops: Stop[] = [],
  ): Promise<Bus[]> {
    if (getConfig().useMockData) return withMockDelay(mockBuses);
    try {
      const res = await apiClient.get<ApiVehiclePositionResponse>('/transit/realtime/vehicles', undefined, signal);
      const routesById = new Map(routes.map((r) => [Number(r.id), r]));
      const stopsById = new Map(stops.map((s) => [Number(s.id), s]));
      return res.vehicles.map((v) => adaptVehicle(v, routesById, stopsById));
    } catch (error) {
      if (isBackendUnavailable(error)) {
        logFallback('getVehicles', error);
        return mockBuses;
      }
      throw error;
    }
  }

  async getVehicle(
    id: string,
    signal?: AbortSignal,
    routes: TransitRoute[] = [],
    stops: Stop[] = [],
  ): Promise<Bus | null> {
    if (getConfig().useMockData) {
      return withMockDelay(mockBuses.find((b) => b.id === id) ?? null);
    }
    try {
      const v = await apiClient.get<ApiVehiclePosition>(`/transit/realtime/vehicles/${encodeURIComponent(id)}`, undefined, signal);
      const routesById = new Map(routes.map((r) => [Number(r.id), r]));
      const stopsById = new Map(stops.map((s) => [Number(s.id), s]));
      return adaptVehicle(v, routesById, stopsById);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      if (isBackendUnavailable(error)) {
        logFallback('getVehicle', error);
        return mockBuses.find((b) => b.id === id) ?? null;
      }
      throw error;
    }
  }

  /** No backend endpoint filters vehicles by route, so this filters the full list client-side. */
  async getRouteVehicles(
    routeId: string,
    signal?: AbortSignal,
    routes: TransitRoute[] = [],
    stops: Stop[] = [],
  ): Promise<Bus[]> {
    if (getConfig().useMockData) {
      return withMockDelay(mockBuses.filter((b) => b.routeId === routeId));
    }
    const all = await this.getVehicles(signal, routes, stops);
    return all.filter((b) => b.routeId === routeId);
  }

  async getVehicleEta(vehicleId: string, signal?: AbortSignal): Promise<ApiVehicleETA | null> {
    try {
      return await apiClient.get<ApiVehicleETA>(`/transit/realtime/vehicles/${encodeURIComponent(vehicleId)}/eta`, undefined, signal);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  }

  // ── Arrivals ──
  // Derived client-side from the vehicle list (no dedicated backend
  // endpoint exists): any vehicle whose next_stop_id matches this stop.

  async getArrivals(stopId: string, signal?: AbortSignal, routes: TransitRoute[] = [], stops: Stop[] = []): Promise<Arrival[]> {
    if (getConfig().useMockData) return withMockDelay(mockArrivals(stopId));
    try {
      const vehicles = await this.getVehicles(signal, routes, stops);
      return vehicles
        .filter((v) => v.nextStopId === stopId && v.eta != null)
        .map((v) => ({
          routeId: v.routeId,
          routeName: v.routeName,
          routeShortName: routes.find((r) => r.id === v.routeId)?.shortName ?? v.routeId,
          routeColor: v.routeColor,
          eta: v.eta as number,
          scheduled: v.status === 'scheduled',
        }));
    } catch (error) {
      if (isBackendUnavailable(error)) {
        logFallback('getArrivals', error);
        return mockArrivals(stopId);
      }
      throw error;
    }
  }

  // ── Journey Search ──
  // The real endpoint takes free-text origin/destination (resolved
  // server-side), not coordinates - callers pass the text the user typed.

  async searchJourneys(
    origin: string,
    destination: string,
    routes: TransitRoute[],
    stops: Stop[],
    options?: JourneySearchOptions,
    signal?: AbortSignal,
  ): Promise<Journey[]> {
    if (getConfig().useMockData) return withMockDelay(mockJourneys);
    try {
      const res = await apiClient.post<ApiJourneySearchResponse>(
        '/transit/journeys/search',
        {
          origin,
          destination,
          objective: options?.objective ?? 'fastest',
          max_walk_m: options?.maxWalkM,
          max_transfers: options?.maxTransfers,
          departure_time: options?.departureTime,
        },
        signal,
      );
      const routesById = new Map(routes.map((r) => [Number(r.id), r]));
      const stopsById = new Map(stops.map((s) => [Number(s.id), s]));
      return res.journeys.map((j, i) =>
        adaptJourney(j, i, routesById, stopsById, res.origin_resolved, res.destination_resolved),
      );
    } catch (error) {
      if (error instanceof ApiError && (error.status === 400 || error.status === 404)) {
        parseJourneySearchError(error);
      }
      if (isBackendUnavailable(error)) {
        logFallback('searchJourneys', error);
        return mockJourneys;
      }
      throw error;
    }
  }

  // ── Search (stop name autocomplete) ──
  // There's no standalone geocoding endpoint; this uses the stop-search
  // filter on GET /transit/stops. Free-text landmarks/aliases the user
  // types directly into the origin/destination fields still resolve
  // correctly via searchJourneys (the backend resolves those server-side)
  // - this list is only for autocomplete suggestions.

  async searchLocations(query: string, signal?: AbortSignal): Promise<SearchResult[]> {
    if (getConfig().useMockData) {
      const lower = query.toLowerCase();
      const filtered = mockSearchResults.filter(
        (r) =>
          r.name.toLowerCase().includes(lower) ||
          (r.subtitle?.toLowerCase().includes(lower) ?? false),
      );
      return withMockDelay(filtered);
    }
    try {
      const res = await apiClient.get<ApiStopListResponse>(
        '/transit/stops',
        query ? { search: query, limit: 30 } : { limit: 30 },
        signal,
      );
      return res.stops.map((s) => ({
        id: String(s.id),
        name: s.name,
        type: 'stop' as const,
        latitude: s.lat,
        longitude: s.lon,
      }));
    } catch (error) {
      if (isBackendUnavailable(error)) {
        logFallback('searchLocations', error);
        const lower = query.toLowerCase();
        return mockSearchResults.filter(
          (r) =>
            r.name.toLowerCase().includes(lower) ||
            (r.subtitle?.toLowerCase().includes(lower) ?? false),
        );
      }
      throw error;
    }
  }

  // ── Auth ──

  async register(email: string, password: string, fullName?: string): Promise<ApiRegisterResponse> {
    return apiClient.post<ApiRegisterResponse>('/auth/register', {
      email,
      password,
      full_name: fullName,
    });
  }

  async login(email: string, password: string): Promise<ApiLoginResponse> {
    return apiClient.post<ApiLoginResponse>('/auth/login', { email, password });
  }

  async getMe(token: string): Promise<ApiUserPublic> {
    return apiClient.get<ApiUserPublic>('/auth/me', undefined, undefined, authHeaders(token));
  }

  // ── Fares ──

  async getFareQuote(rideLegCount: number): Promise<ApiFareQuote> {
    return apiClient.post<ApiFareQuote>('/fares/quote', { ride_leg_count: rideLegCount });
  }

  // ── Tickets (require auth) ──

  async purchaseTicket(
    token: string,
    journeyData: Record<string, unknown>,
    rideLegCount: number,
  ): Promise<ApiTicketResponse> {
    return apiClient.post<ApiTicketResponse>(
      '/tickets',
      { journey_data: journeyData, ride_leg_count: rideLegCount },
      undefined,
      authHeaders(token),
    );
  }

  async listTickets(token: string): Promise<ApiTicketResponse[]> {
    const res = await apiClient.get<ApiTicketListResponse>('/tickets', undefined, undefined, authHeaders(token));
    return res.tickets;
  }

  async getTicket(token: string, ticketId: number): Promise<ApiTicketResponse | null> {
    try {
      return await apiClient.get<ApiTicketResponse>(`/tickets/${ticketId}`, undefined, undefined, authHeaders(token));
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  }

  async revokeTicket(token: string, ticketId: number): Promise<ApiTicketResponse> {
    return apiClient.post<ApiTicketResponse>(`/tickets/${ticketId}/revoke`, undefined, undefined, authHeaders(token));
  }

  async validateTicket(token: string, qrPayload: string): Promise<ApiValidationResult> {
    return apiClient.post<ApiValidationResult>(
      '/tickets/validate',
      { qr_payload: qrPayload },
      undefined,
      authHeaders(token),
    );
  }

  // ── AI / voice conversation ──
  // The endpoint takes multipart/form-data (a text message XOR an audio
  // file), never JSON - this is a real constraint of the FastAPI Form/File
  // dependency on the backend, not a choice made here.

  async converseWithText(message: string, token?: string, signal?: AbortSignal): Promise<ApiConverseResponse> {
    const form = new FormData();
    form.append('message', message);
    return apiClient.postForm<ApiConverseResponse>('/ai/converse', form, signal, authHeaders(token));
  }

  async converseWithAudio(audio: Blob, filename: string, token?: string, signal?: AbortSignal): Promise<ApiConverseResponse> {
    const form = new FormData();
    // React Native's FormData.append only takes (name, value) - no filename
    // param like the browser's does - so the 3rd arg is cast through `any`
    // to stay source-compatible with both environments at runtime.
    (form.append as (name: string, value: unknown, filename?: string) => void)('audio', audio, filename);
    return apiClient.postForm<ApiConverseResponse>('/ai/converse', form, signal, authHeaders(token));
  }

  /**
   * Ask the AI assistant a free-form question (e.g. "how do I get from
   * Saddar to PIMS Hospital") and get back a UI-ready result: adapted
   * journeys (same shape searchJourneys returns) when the assistant found
   * a route, a clarification prompt when it needs a more specific
   * origin/destination, or just a conversational reply otherwise.
   */
  async askAssistant(
    message: string,
    routes: TransitRoute[],
    stops: Stop[],
    token?: string,
    signal?: AbortSignal,
  ): Promise<AssistantResult> {
    const res = await this.converseWithText(message, token, signal);
    const routesById = new Map(routes.map((r) => [Number(r.id), r]));
    const stopsById = new Map(stops.map((s) => [Number(s.id), s]));

    const journeys = res.structured_journeys
      ? res.structured_journeys.journeys.map((j, i) =>
          adaptJourney(
            j,
            i,
            routesById,
            stopsById,
            res.structured_journeys!.origin_resolved,
            res.structured_journeys!.destination_resolved,
          ),
        )
      : null;

    return {
      reply: res.text_response,
      journeys,
      clarification: res.clarification_needed
        ? {
            field: res.clarification_needed.field,
            candidateNames: res.clarification_needed.candidates.map((c) => c.name),
          }
        : null,
    };
  }
}

export interface AssistantResult {
  reply: string;
  journeys: Journey[] | null;
  clarification: { field: 'origin' | 'destination'; candidateNames: string[] } | null;
}

// ── Singleton ──

export const transitService = new TransitService();

// ── Arrival type (shared domain model) ──

export interface Arrival {
  routeId: string;
  routeName: string;
  routeShortName: string;
  routeColor: string;
  eta: number; // minutes
  scheduled: boolean;
}

// ── Mock arrival generator ──

function mockArrivals(stopId: string): Arrival[] {
  const stop = mockStops.find((s) => s.id === stopId);
  if (!stop) return [];
  return stop.routeIds.flatMap((routeId) => {
    const route = mockRoutes.find((r) => r.id === routeId);
    if (!route) return [];
    return [{
      routeId: route.id,
      routeName: route.name,
      routeShortName: route.shortName,
      routeColor: route.color,
      eta: Math.floor(Math.random() * 15) + 1,
      scheduled: true,
    }];
  });
}
