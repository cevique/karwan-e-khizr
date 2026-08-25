// ── Karwan-e-Khizr: Transit Service ──
// Abstraction layer between UI and data sources (FastAPI ↔ mock fallback).
//
// Data flow:
//   UI → Hooks → TransitService → API Client → FastAPI → PostgreSQL/PostGIS
//                              ↘ Mock Data (when backend is unavailable)
//
// The service attempts real API calls first and falls back to mock data when:
//   - The backend is unreachable (NetworkError, TimeoutError)
//   - The endpoint does not exist (404)
//   - The server returns an error (5xx)
//
// When the backend endpoints are implemented, the fallback will be bypassed
// automatically and real data will flow through the same interface.

import type { Bus, Stop, TransitRoute, Journey, SearchResult } from '../types';
import { apiClient } from './api-client';
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
    // 404 = endpoint not implemented, 5xx = server error
    return error.status === 404 || error.status >= 500;
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

// ── Service class ──

class TransitService {
  // ── Routes ──

  async getRoutes(signal?: AbortSignal): Promise<TransitRoute[]> {
    if (getConfig().useMockData) return withMockDelay(mockRoutes);
    try {
      return await apiClient.get<TransitRoute[]>('/routes', undefined, signal);
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
      return await apiClient.get<TransitRoute>(`/routes/${encodeURIComponent(id)}`, undefined, signal);
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
      return await apiClient.get<Stop[]>('/stops', undefined, signal);
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
      return await apiClient.get<Stop>(`/stops/${encodeURIComponent(id)}`, undefined, signal);
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

  async getVehicles(signal?: AbortSignal): Promise<Bus[]> {
    if (getConfig().useMockData) return withMockDelay(mockBuses);
    try {
      return await apiClient.get<Bus[]>('/vehicles', undefined, signal);
    } catch (error) {
      if (isBackendUnavailable(error)) {
        logFallback('getVehicles', error);
        return mockBuses;
      }
      throw error;
    }
  }

  async getVehicle(id: string, signal?: AbortSignal): Promise<Bus | null> {
    if (getConfig().useMockData) {
      return withMockDelay(mockBuses.find((b) => b.id === id) ?? null);
    }
    try {
      return await apiClient.get<Bus>(`/vehicles/${encodeURIComponent(id)}`, undefined, signal);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      if (isBackendUnavailable(error)) {
        logFallback('getVehicle', error);
        return mockBuses.find((b) => b.id === id) ?? null;
      }
      throw error;
    }
  }

  async getRouteVehicles(routeId: string, signal?: AbortSignal): Promise<Bus[]> {
    if (getConfig().useMockData) {
      return withMockDelay(mockBuses.filter((b) => b.routeId === routeId));
    }
    try {
      return await apiClient.get<Bus[]>(`/routes/${encodeURIComponent(routeId)}/vehicles`, undefined, signal);
    } catch (error) {
      if (isBackendUnavailable(error)) {
        logFallback('getRouteVehicles', error);
        return mockBuses.filter((b) => b.routeId === routeId);
      }
      throw error;
    }
  }

  // ── Arrivals ──

  async getArrivals(stopId: string, signal?: AbortSignal): Promise<Arrival[]> {
    if (getConfig().useMockData) return withMockDelay(mockArrivals(stopId));
    try {
      return await apiClient.get<Arrival[]>(`/stops/${encodeURIComponent(stopId)}/arrivals`, undefined, signal);
    } catch (error) {
      if (isBackendUnavailable(error)) {
        logFallback('getArrivals', error);
        return mockArrivals(stopId);
      }
      throw error;
    }
  }

  // ── Journey Search ──

  async searchJourneys(
    originLat: number,
    originLng: number,
    destLat: number,
    destLng: number,
    signal?: AbortSignal,
  ): Promise<Journey[]> {
    if (getConfig().useMockData) return withMockDelay(mockJourneys);
    try {
      return await apiClient.post<Journey[]>(
        '/journeys/search',
        {
          origin: { latitude: originLat, longitude: originLng },
          destination: { latitude: destLat, longitude: destLng },
        },
        signal,
      );
    } catch (error) {
      if (isBackendUnavailable(error)) {
        logFallback('searchJourneys', error);
        return mockJourneys;
      }
      throw error;
    }
  }

  // ── Search / Geocoding ──

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
      return await apiClient.get<SearchResult[]>(
        '/search',
        { q: query },
        signal,
      );
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
