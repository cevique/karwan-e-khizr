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
import { transitService } from '../services/transit-service';
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

export function useVehicles(): AsyncResult<Bus[]> & { refetch: () => void } {
  return useAsyncData((signal) => transitService.getVehicles(signal), []);
}

export function useVehicle(id: string | null): AsyncResult<Bus | null> & { refetch: () => void } {
  return useAsyncData(
    (signal) => (id ? transitService.getVehicle(id, signal) : Promise.resolve(null)),
    [id],
  );
}

export function useRouteVehicles(routeId: string | null): AsyncResult<Bus[]> & { refetch: () => void } {
  return useAsyncData(
    (signal) => (routeId ? transitService.getRouteVehicles(routeId, signal) : Promise.resolve([])),
    [routeId],
  );
}

// ── Arrival hook ──

export function useArrivals(stopId: string | null): AsyncResult<Arrival[]> & { refetch: () => void } {
  return useAsyncData(
    (signal) => (stopId ? transitService.getArrivals(stopId, signal) : Promise.resolve([])),
    [stopId],
  );
}

// ── Journey hooks ──

export function useJourneySearch(
  originLat: number | null,
  originLng: number | null,
  destLat: number | null,
  destLng: number | null,
): AsyncResult<Journey[]> & { refetch: () => void } {
  return useAsyncData(
    (signal) =>
      originLat != null && originLng != null && destLat != null && destLng != null
        ? transitService.searchJourneys(originLat, originLng, destLat, destLng, signal)
        : Promise.resolve([]),
    [originLat, originLng, destLat, destLng],
  );
}

// ── Search hook ──

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
// Fetches routes, stops, and vehicles in parallel — useful for the map layer.

export interface TransitData {
  routes: TransitRoute[];
  stops: Stop[];
  vehicles: Bus[];
}

export function useTransitData(): AsyncResult<TransitData> & { refetch: () => void } {
  return useAsyncData(async (signal) => {
    const [routes, stops, vehicles] = await Promise.all([
      transitService.getRoutes(signal),
      transitService.getStops(signal),
      transitService.getVehicles(signal),
    ]);
    return { routes, stops, vehicles };
  }, []);
}
