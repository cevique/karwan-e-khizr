// ── Karwan-e-Khizr: Frontend Configuration ──
// Centralised config for API URLs and runtime flags.
// Must be initialised once at app startup via initConfig().

export interface AppConfig {
  /** FastAPI base URL (e.g. http://localhost:8000/api/v1) */
  apiUrl: string;
  /** When true, skip API calls and return mock data directly */
  useMockData: boolean;
  /** Request timeout in milliseconds */
  requestTimeoutMs: number;
}

let config: AppConfig = {
  apiUrl: 'http://localhost:8000/api/v1',
  useMockData: true,
  requestTimeoutMs: 10000,
};

/** Initialise the frontend configuration. Call once at app startup. */
export function initConfig(overrides: Partial<AppConfig>): void {
  config = { ...config, ...overrides };
}

/** Retrieve the current configuration (read-only snapshot). */
export function getConfig(): Readonly<AppConfig> {
  return config;
}
