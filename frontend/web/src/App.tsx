import { useState, useCallback, useEffect, createContext, useContext } from 'react';
import type { Bus, Stop, Journey, TransitRoute, RouteStops } from '@shared/types';
import type { ApiUserPublic } from '@shared/types/api';
import { initConfig } from '@shared/services/config';
import { useTransitData } from '@shared/hooks/useTransitData';
import { transitService } from '@shared/services/transit-service';
import { ApiError } from '@shared/services/api-client';
import { DesktopShell } from './components/shell/DesktopShell';
import { MobileShell } from './components/shell/MobileShell';
import { useMediaQuery } from './hooks/useMediaQuery';

// ── Initialise shared config from Vite env ──
initConfig({
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  // Real backend endpoints exist now, so mock data is opt-in (set
  // VITE_USE_MOCK_DATA=true to force it, e.g. for offline demos).
  useMockData: import.meta.env.VITE_USE_MOCK_DATA === 'true',
});

const TOKEN_STORAGE_KEY = 'kek_auth_token';

// ── App State ──
export type Screen = 'home' | 'search' | 'routes' | 'journey-detail' | 'saved' | 'settings' | 'auth' | 'tickets';

export interface AppState {
  screen: Screen;
  previousScreen: Screen | null;
  selectedBusId: string | null;
  selectedStop: Stop | null;
  selectedJourney: Journey | null;
  selectedRoute: TransitRoute | null;
  routeStops: RouteStops | null;
  routeGeometry: [number, number][];
  searchOrigin: string;
  searchDestination: string;
}

interface TransitDataContext {
  routes: TransitRoute[];
  stops: Stop[];
  vehicles: Bus[];
  transitLoading: boolean;
  transitError: Error | null;
}

interface AuthContext {
  user: ApiUserPublic | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

interface AppContextType {
  state: AppState;
  selectedBus: Bus | null;
  navigate: (screen: Screen) => void;
  goBack: () => void;
  selectBus: (bus: Bus | null) => void;
  selectStop: (stop: Stop | null) => void;
  selectRoute: (route: TransitRoute | null) => void;
  selectJourney: (journey: Journey | null) => void;
  setSearchOrigin: (origin: string) => void;
  setSearchDestination: (dest: string) => void;
  savedJourneys: Journey[];
  saveJourney: (journey: Journey) => void;
  unsaveJourney: (journeyId: string) => void;
  isJourneySaved: (journeyId: string) => boolean;
  transit: TransitDataContext;
  auth: AuthContext;
}

const defaultState: AppState = {
  screen: 'home',
  previousScreen: null,
  selectedBusId: null,
  selectedStop: null,
  selectedJourney: null,
  selectedRoute: null,
  routeStops: null,
  routeGeometry: [],
  searchOrigin: '',
  searchDestination: '',
};

const SAVED_JOURNEYS_KEY = 'kek_saved_journeys';

const AppContext = createContext<AppContextType | null>(null);

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}

export default function App() {
  const [state, setState] = useState<AppState>(defaultState);
  const isDesktop = useMediaQuery('(min-width: 768px)');

  // Saved journeys (persisted in localStorage)
  const [savedJourneys, setSavedJourneys] = useState<Journey[]>(() => {
    try {
      const raw = localStorage.getItem(SAVED_JOURNEYS_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch { return []; }
  });

  const saveJourney = useCallback((journey: Journey) => {
    setSavedJourneys((prev) => {
      if (prev.some(j => j.id === journey.id)) return prev;
      const next = [...prev, journey];
      try { localStorage.setItem(SAVED_JOURNEYS_KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  const unsaveJourney = useCallback((journeyId: string) => {
    setSavedJourneys((prev) => {
      const next = prev.filter(j => j.id !== journeyId);
      try { localStorage.setItem(SAVED_JOURNEYS_KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  const isJourneySaved = useCallback((journeyId: string) => {
    return savedJourneys.some(j => j.id === journeyId);
  }, [savedJourneys]);

  // Fetch transit data through the service layer
  const { data: transitData, loading: transitLoading, error: transitError } = useTransitData();

  // ── Auth state ──
  const [token, setToken] = useState<string | null>(() => {
    try { return localStorage.getItem(TOKEN_STORAGE_KEY); } catch { return null; }
  });
  const [user, setUser] = useState<ApiUserPublic | null>(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Restore the user profile on load if a token is already stored.
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    transitService.getMe(token)
      .then((u) => { if (!cancelled) setUser(u); })
      .catch(() => {
        // Stored token is no longer valid - drop it silently.
        if (!cancelled) {
          setToken(null);
          try { localStorage.removeItem(TOKEN_STORAGE_KEY); } catch { /* ignore */ }
        }
      });
    return () => { cancelled = true; };
  }, [token]);

  const login = useCallback(async (email: string, password: string) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const res = await transitService.login(email, password);
      setToken(res.access_token);
      setUser(res.user);
      try { localStorage.setItem(TOKEN_STORAGE_KEY, res.access_token); } catch { /* ignore */ }
    } catch (err) {
      setAuthError(describeAuthError(err));
      throw err;
    } finally {
      setAuthLoading(false);
    }
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      await transitService.register(email, password, fullName);
      // Registration doesn't return a session - log in right after.
      const res = await transitService.login(email, password);
      setToken(res.access_token);
      setUser(res.user);
      try { localStorage.setItem(TOKEN_STORAGE_KEY, res.access_token); } catch { /* ignore */ }
    } catch (err) {
      setAuthError(describeAuthError(err));
      throw err;
    } finally {
      setAuthLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setSavedJourneys([]);
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem(SAVED_JOURNEYS_KEY);
    } catch { /* ignore */ }
  }, []);

  const clearError = useCallback(() => setAuthError(null), []);

  const navigate = useCallback((screen: Screen) => {
    setState((prev) => ({ ...prev, screen, previousScreen: prev.screen }));
  }, []);

  const goBack = useCallback(() => {
    setState((prev) => ({
      ...prev,
      screen: prev.previousScreen ?? 'home',
      previousScreen: null,
    }));
  }, []);

  const selectBus = useCallback((bus: Bus | null) => {
    setState((prev) => ({ ...prev, selectedBusId: bus?.id ?? null, selectedStop: null }));
  }, []);

  const selectStop = useCallback((stop: Stop | null) => {
    setState((prev) => ({ ...prev, selectedStop: stop, selectedBus: null }));
  }, []);

  const selectRoute = useCallback(async (route: TransitRoute | null) => {
    if (!route) {
      setState((prev) => ({ ...prev, selectedRoute: null, routeStops: null, routeGeometry: [] }));
      return;
    }
    setState((prev) => ({ ...prev, selectedRoute: route, routeStops: null, routeGeometry: [] }));
    try {
      const [data, geometry] = await Promise.all([
        transitService.getRouteStops(route.id),
        transitService.getRouteGeometry(route.id),
      ]);
      setState((prev) => {
        if (prev.selectedRoute?.id !== route.id) return prev;
        return { ...prev, routeStops: data, routeGeometry: geometry };
      });
    } catch {
      // Silently handle - stops just won't show
    }
  }, []);

  const selectJourney = useCallback(async (journey: Journey | null) => {
    if (!journey) {
      setState((prev) => ({
        ...prev,
        selectedJourney: null,
        selectedRoute: null,
        routeStops: null,
        routeGeometry: [],
      }));
      return;
    }
    setState((prev) => ({
      ...prev,
      selectedJourney: journey,
      routeStops: null,
      routeGeometry: [],
      screen: 'journey-detail',
      previousScreen: prev.screen,
    }));
    // Load polyline for each transit segment and clip to the journey portion
    const transitSegs = journey.segments.filter(
      (s): s is import('@shared/types').TransitSegment => s.type !== 'walk' && s.type !== 'transfer',
    );
    if (transitSegs.length === 0) return;
    // Use the first transit segment for the map polyline
    const seg = transitSegs[0];
    try {
      const [data, geometry] = await Promise.all([
        transitService.getRouteStops(seg.routeId),
        transitService.getRouteGeometry(seg.routeId),
      ]);
      const clipped = clipGeometryToSegment(
        geometry,
        [seg.fromStop.longitude, seg.fromStop.latitude],
        [seg.toStop.longitude, seg.toStop.latitude],
      );
      setState((prev) => {
        if (prev.selectedJourney?.id !== journey.id) return prev;
        return { ...prev, routeStops: data, routeGeometry: clipped };
      });
    } catch {
      // Silently handle - polyline just won't show
    }
  }, []);

  const setSearchOrigin = useCallback((origin: string) => {
    setState((prev) => ({ ...prev, searchOrigin: origin }));
  }, []);

  const setSearchDestination = useCallback((dest: string) => {
    setState((prev) => ({ ...prev, searchDestination: dest }));
  }, []);

  const transitContext: TransitDataContext = {
    routes: transitData?.routes ?? [],
    stops: transitData?.stops ?? [],
    vehicles: transitData?.vehicles ?? [],
    transitLoading,
    transitError,
  };

  // Derive selectedBus from live vehicle data so the popup updates on every poll
  const selectedBus = transitContext.vehicles.find(v => v.id === state.selectedBusId) ?? null;

  const authContext: AuthContext = {
    user, token, loading: authLoading, error: authError,
    login, register, logout, clearError,
  };

  const contextValue: AppContextType = {
    state,
    selectedBus,
    navigate,
    goBack,
    selectBus,
    selectStop,
    selectRoute,
    selectJourney,
    setSearchOrigin,
    setSearchDestination,
    savedJourneys,
    saveJourney,
    unsaveJourney,
    isJourneySaved,
    transit: transitContext,
    auth: authContext,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {isDesktop ? <DesktopShell /> : <MobileShell />}
    </AppContext.Provider>
  );
}

function describeAuthError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 401) return 'Incorrect email or password.';
    if (err.status === 409) return 'An account with this email already exists.';
    if (err.status === 422) return 'Please check the details you entered.';
    const body = err.body as { detail?: string } | undefined;
    if (typeof body?.detail === 'string') return body.detail;
  }
  return 'Something went wrong. Please try again.';
}

/** Find the index of the closest point in `coords` to `target`. */
function closestIndex(coords: [number, number][], target: [number, number]): number {
  let best = 0;
  let bestDist = Infinity;
  for (let i = 0; i < coords.length; i++) {
    const dx = coords[i][0] - target[0];
    const dy = coords[i][1] - target[1];
    const d = dx * dx + dy * dy;
    if (d < bestDist) { bestDist = d; best = i; }
  }
  return best;
}

/** Clip a full route geometry to the portion between two stops. */
function clipGeometryToSegment(
  geometry: [number, number][],
  from: [number, number],
  to: [number, number],
): [number, number][] {
  if (geometry.length === 0) return [];
  const i = closestIndex(geometry, from);
  const j = closestIndex(geometry, to);
  const [start, end] = i <= j ? [i, j] : [j, i];
  return geometry.slice(start, end + 1);
}
