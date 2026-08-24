import { useState, useCallback, createContext, useContext } from 'react';
import type { Bus, Stop, Journey } from '@shared/types';
import { DesktopShell } from './components/shell/DesktopShell';
import { MobileShell } from './components/shell/MobileShell';
import { useMediaQuery } from './hooks/useMediaQuery';

// ── App State ──
export type Screen = 'home' | 'search' | 'routes' | 'journey-detail' | 'saved' | 'settings';

export interface AppState {
  screen: Screen;
  previousScreen: Screen | null;
  selectedBus: Bus | null;
  selectedStop: Stop | null;
  selectedJourney: Journey | null;
  searchOrigin: string;
  searchDestination: string;
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

  const contextValue: AppContextType = {
    state,
    navigate,
    goBack,
    selectBus,
    selectStop,
    selectJourney,
    setSearchOrigin,
    setSearchDestination,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {isDesktop ? <DesktopShell /> : <MobileShell />}
    </AppContext.Provider>
  );
}
