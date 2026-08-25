// ── Karwan-e-Khizr: Shared Module Exports ──
export * from './types';
export * from './mocks/stops';
export * from './mocks/routes';
export * from './mocks/buses';
export * from './mocks/journeys';
export * from './mocks/search';
export * from './constants';

// Service layer
export { initConfig, getConfig } from './services/config';
export type { AppConfig } from './services/config';
export { apiClient, ApiError, NetworkError, TimeoutError } from './services/api-client';
export { transitService } from './services/transit-service';
export type { Arrival } from './services/transit-service';

// React hooks
export {
  useRoutes,
  useRoute,
  useStops,
  useStop,
  useVehicles,
  useVehicle,
  useRouteVehicles,
  useArrivals,
  useJourneySearch,
  useSearchResults,
  useTransitData,
} from './hooks/useTransitData';
export type { AsyncResult, TransitData } from './hooks/useTransitData';
