// ── Karwan-e-Khizr: Transit Data Hooks ──
// React hooks that bridge the TransitService to UI components.
//
// Each hook returns { data, loading, error } and handles:
//   - Automatic fetching on mount
//   - Request cancellation on unmount
//   - Loading / error / empty state management
//
// Components must consume transit data through these hooks,
// never by importing mock data or calling the API client directly.

import { useState, useEffect, useRef, useCallback } from 'react';
import type { Bus, Stop, TransitRoute, Journey, SearchResult } from '../types';
import type { JourneyObjective } from '../types/api';
import { transitService, JourneySearchOptions } from '../services/transit-service';
import type { Arrival } from '../services/transit-service';

// ── Generic result shape ──

export interface AsyncResult<T> {
  data: T;
  loading: boolean;
  error: Error | null;
}

// ── Generic fetch hook ──

function useAsyncData<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: unknown[] = [],
): AsyncResult<T> & { refetch: () => void } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  const execute = useCallback(() => {
    // Cancel any in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);

    fetcher(controller.signal)
      .then((result) => {
        if (!mountedRef.current) return;
        setData(result);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (!mountedRef.current) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        if (err instanceof Error && err.message === 'Request was cancelled') return;
        setError(err instanceof Error ? err : new Error(String(err)));
        setLoading(false);
      });
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    mountedRef.current = true;
    execute();
    return () => {
      mountedRef.current = false;
      abortRef.current?.abort();
    };
  }, [execute]);

  return { data: data as T, loading, error, refetch: execute };
}

// ── Route hooks ──

export function useRoutes(): AsyncResult<TransitRoute[]> & { refetch: () => void } {
  return useAsyncData((signal) => transitService.getRoutes(signal), []);
}

export function useRoute(id: string | null): AsyncResult<TransitRoute | null> & { refetch: () => void } {
  return useAsyncData(
    (signal) => (id ? transitService.getRoute(id, signal) : Promise.resolve(null)),
    [id],
  );
}

// ── Stop hooks ──

export function useStops(): AsyncResult<Stop[]> & { refetch: () => void } {
  return useAsyncData((signal) => transitService.getStops(signal), []);
}

export function useStop(id: string | null): AsyncResult<Stop | null> & { refetch: () => void } {
  return useAsyncData(
    (signal) => (id ? transitService.getStop(id, signal) : Promise.resolve(null)),
    [id],
  );
}

// ── Vehicle hooks ──
// Vehicles are enriched with route/stop names client-side, so these
// accept the already-loaded routes/stops (e.g. from useTransitData) -
// avoids a redundant fetch and keeps names consistent app-wide.

export function useVehicles(routes: TransitRoute[] = [], stops: Stop[] = []): AsyncResult<Bus[]> & { refetch: () => void } {
  return useAsyncData((signal) => transitService.getVehicles(signal, routes, stops), [routes, stops]);
}

export function useVehicle(
  id: string | null,
  routes: TransitRoute[] = [],
  stops: Stop[] = [],
): AsyncResult<Bus | null> & { refetch: () => void } {
  return useAsyncData(
    (signal) => (id ? transitService.getVehicle(id, signal, routes, stops) : Promise.resolve(null)),
    [id, routes, stops],
  );
}

export function useRouteVehicles(
  routeId: string | null,
  routes: TransitRoute[] = [],
  stops: Stop[] = [],
): AsyncResult<Bus[]> & { refetch: () => void } {
  return useAsyncData(
    (signal) => (routeId ? transitService.getRouteVehicles(routeId, signal, routes, stops) : Promise.resolve([])),
    [routeId, routes, stops],
  );
}

// ── Arrival hook ──

export function useArrivals(
  stopId: string | null,
  routes: TransitRoute[] = [],
  stops: Stop[] = [],
): AsyncResult<Arrival[]> & { refetch: () => void } {
  return useAsyncData(
    (signal) => (stopId ? transitService.getArrivals(stopId, signal, routes, stops) : Promise.resolve([])),
    [stopId, routes, stops],
  );
}

// ── Journey hooks ──
// The real search takes free-text origin/destination (server-resolved),
// and needs the already-loaded routes/stops to enrich leg details with
// names/colors - pass `enabled: false` until the user actually submits a
// search, since this fires on every dependency change otherwise.

export function useJourneySearch(
  origin: string,
  destination: string,
  routes: TransitRoute[],
  stops: Stop[],
  enabled: boolean,
  options?: JourneySearchOptions,
): AsyncResult<Journey[]> & { refetch: () => void } {
  return useAsyncData(
    (signal) =>
      enabled && origin.trim() && destination.trim()
        ? transitService.searchJourneys(origin, destination, routes, stops, options, signal)
        : Promise.resolve([]),
    [origin, destination, routes, stops, enabled, options?.objective, options?.maxWalkM, options?.maxTransfers],
  );
}

// ── Search hook (stop-name autocomplete) ──

export function useSearchResults(query: string): AsyncResult<SearchResult[]> & { refetch: () => void } {
  return useAsyncData(
    (signal) =>
      query.length > 0
        ? transitService.searchLocations(query, signal)
        : transitService.searchLocations('', signal),
    [query],
  );
}

// ── Preloaded data hook ──
// Fetches routes and stops first (vehicles need them for enrichment),
// then vehicles - useful for the map layer and as the shared app-wide
// transit context (see App.tsx).

export interface TransitData {
  routes: TransitRoute[];
  stops: Stop[];
  vehicles: Bus[];
}

export function useTransitData(): AsyncResult<TransitData> & { refetch: () => void } {
  return useAsyncData(async (signal) => {
    const [routes, stops] = await Promise.all([
      transitService.getRoutes(signal),
      transitService.getStops(signal),
    ]);
    const vehicles = await transitService.getVehicles(signal, routes, stops);
    return { routes, stops, vehicles };
  }, []);
}

export type { JourneyObjective };
