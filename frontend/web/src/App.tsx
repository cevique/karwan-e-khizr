import { useState, useCallback, useEffect, createContext, useContext } from 'react';
import type { Bus, Stop, Journey, TransitRoute } from '@shared/types';
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
  selectedBus: Bus | null;
  selectedStop: Stop | null;
  selectedJourney: Journey | null;
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
  navigate: (screen: Screen) => void;
  goBack: () => void;
  selectBus: (bus: Bus | null) => void;
  selectStop: (stop: Stop | null) => void;
  selectJourney: (journey: Journey | null) => void;
  setSearchOrigin: (origin: string) => void;
  setSearchDestination: (dest: string) => void;
  transit: TransitDataContext;
  auth: AuthContext;
}

const defaultState: AppState = {
  screen: 'home',
  previousScreen: null,
  selectedBus: null,
  selectedStop: null,
  selectedJourney: null,
  searchOrigin: 'Ammar Chowk',
  searchDestination: '',
};

const AppContext = createContext<AppContextType | null>(null);

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}

export default function App() {
  const [state, setState] = useState<AppState>(defaultState);
  const isDesktop = useMediaQuery('(min-width: 768px)');

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
    try { localStorage.removeItem(TOKEN_STORAGE_KEY); } catch { /* ignore */ }
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
    setState((prev) => ({ ...prev, selectedBus: bus, selectedStop: null }));
  }, []);

  const selectStop = useCallback((stop: Stop | null) => {
    setState((prev) => ({ ...prev, selectedStop: stop, selectedBus: null }));
  }, []);

  const selectJourney = useCallback((journey: Journey | null) => {
    setState((prev) => ({
      ...prev,
      selectedJourney: journey,
      screen: journey ? 'journey-detail' : prev.screen,
      previousScreen: journey ? prev.screen : prev.previousScreen,
    }));
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

  const authContext: AuthContext = {
    user, token, loading: authLoading, error: authError,
    login, register, logout, clearError,
  };

  const contextValue: AppContextType = {
    state,
    navigate,
    goBack,
    selectBus,
    selectStop,
    selectJourney,
    setSearchOrigin,
    setSearchDestination,
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
