// ── Karwan-e-Khizr: Backend API Types ──
// These interfaces mirror the FastAPI response/request bodies exactly
// (see backend/app/routing/schemas.py, app/simulation/schemas.py,
// app/transit_catalog/schemas.py, app/users/schemas.py,
// app/ticketing/schemas.py). Keep these in lockstep with the backend -
// they are the ONLY place raw wire shapes should appear. UI-facing code
// should consume the mapped view-model types in `./index` instead.

// ── Transit catalog (GET /transit/routes, GET /transit/stops) ──

export interface ApiRoute {
  id: number;
  agency_id: number;
  agency_name: string;
  short_name: string;
  long_name: string | null;
  route_type: 'bus' | 'metro' | 'feeder';
  color: string | null;
  text_color: string | null;
  has_geometry: boolean;
}

export interface ApiRouteListResponse {
  routes: ApiRoute[];
  total: number;
  limit: number;
  offset: number;
}

export interface ApiStop {
  id: number;
  name: string;
  external_key: string | null;
  lat: number;
  lon: number;
  zone_id: string | null;
  coordinate_confidence: 'HIGH' | 'APPROXIMATE' | 'UNKNOWN' | null;
}

export interface ApiStopListResponse {
  stops: ApiStop[];
  total: number;
  limit: number;
  offset: number;
}

// ── Realtime vehicles (GET /transit/realtime/vehicles) ──

export interface ApiVehiclePosition {
  id: number;
  label: string;
  route_id: number;
  trip_id: number;
  latitude: number;
  longitude: number;
  bearing: number | null;
  speed: number | null; // metres/second
  status: 'scheduled' | 'active' | 'completed';
  source: 'simulated' | 'realtime';
  timestamp: string;
  next_stop_id: number | null;
  eta_seconds: number | null;
}

export interface ApiVehiclePositionResponse {
  vehicles: ApiVehiclePosition[];
}

export interface ApiVehicleETA {
  vehicle_id: number;
  next_stop_id: number;
  baseline_eta_seconds: number;
  predicted_eta_seconds: number | null;
  delay_seconds: number | null;
  source: 'simulated' | 'realtime';
}

// ── Journey search (POST /transit/journeys/search) ──

export type JourneyObjective = 'fastest' | 'fewest_transfers' | 'least_walking';

export interface ApiJourneySearchRequest {
  origin: string;
  destination: string;
  objective?: JourneyObjective;
  max_walk_m?: number;
  max_transfers?: number;
  departure_time?: string;
}

export interface ApiFareQuote {
  base_fare: number;
  per_leg_fare: number;
  total: number;
  currency: string;
}

export interface ApiLeg {
  type: 'walk' | 'ride';
  route_id: number | null;
  trip_id: number | null;
  start_stop_id: number;
  end_stop_id: number;
  start_lat: number;
  start_lon: number;
  end_lat: number;
  end_lon: number;
  duration_s: number;
  distance_m: number | null;
  geometry: Record<string, unknown> | null;
  departure_time: string | null;
  arrival_time: string | null;
}

export interface ApiJourney {
  legs: ApiLeg[];
  total_duration_s: number;
  total_walk_m: number;
  transfer_count: number;
  fare: ApiFareQuote | null;
}

export interface ApiLocationResolved {
  name: string;
  lat: number;
  lon: number;
}

export interface ApiJourneySearchResponse {
  journeys: ApiJourney[];
  origin_resolved: ApiLocationResolved;
  destination_resolved: ApiLocationResolved;
}

export interface ApiAmbiguousLocationError {
  error: 'ambiguous_origin' | 'ambiguous_destination';
  candidates: ApiLocationResolved[];
}

// ── Auth (POST /auth/register, /auth/login, GET /auth/me) ──

export interface ApiRegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface ApiRegisterResponse {
  id: number;
  email: string;
  role: string;
}

export interface ApiLoginRequest {
  email: string;
  password: string;
}

export interface ApiUserPublic {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
}

export interface ApiLoginResponse {
  access_token: string;
  token_type: string;
  user: ApiUserPublic;
}

// ── Fares (POST /fares/quote) ──

export interface ApiFareQuoteRequest {
  ride_leg_count: number;
}

// ── Tickets (POST /tickets, GET /tickets, etc.) ──

export type ApiTicketStatus = 'ACTIVE' | 'USED' | 'EXPIRED' | 'REVOKED';

export interface ApiTicketResponse {
  id: number;
  status: ApiTicketStatus;
  fare_charged: number;
  currency: string;
  qr_payload: string;
  created_at: string;
  expires_at: string | null;
  used_at: string | null;
  ride_leg_count: number;
  journey_data: Record<string, unknown>;
}

export interface ApiTicketListResponse {
  tickets: ApiTicketResponse[];
}

export interface ApiTicketPurchaseRequest {
  journey_data: Record<string, unknown>;
  ride_leg_count: number;
}

export interface ApiValidationRequest {
  qr_payload: string;
}

export interface ApiValidationResult {
  valid: boolean;
  ticket_id: number | null;
  status: ApiTicketStatus | null;
  reason: string | null;
}

// ── AI / voice (POST /ai/converse) ──

export interface ApiConverseClarification {
  field: 'origin' | 'destination';
  candidates: ApiLocationResolved[];
}

export interface ApiConverseResponse {
  text_response: string;
  structured_journeys: ApiJourneySearchResponse | null;
  clarification_needed: ApiConverseClarification | null;
  text_response_error?: string | null;
}
