// ── Karwan-e-Khizr: API Client ──
// Centralised HTTP client for FastAPI communication.
// Handles base URL, serialisation, timeouts, cancellation, and errors.

import { getConfig } from './config';

// ── Error types ──

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends Error {
  constructor() {
    super('Request timed out');
    this.name = 'TimeoutError';
  }
}

// ── Internal helpers ──

function buildUrl(path: string, params?: Record<string, string | number | boolean | undefined>): string {
  const base = getConfig().apiUrl.replace(/\/$/, '');
  const url = new URL(`${base}${path}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
  }
  return url.toString();
}

async function executeRequest<T>(
  method: string,
  path: string,
  options?: {
    params?: Record<string, string | number | boolean | undefined>;
    body?: unknown;
    signal?: AbortSignal;
  },
): Promise<T> {
  const { requestTimeoutMs } = getConfig();

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), requestTimeoutMs);

  // Forward external abort to internal controller
  if (options?.signal) {
    if (options.signal.aborted) {
      clearTimeout(timeoutId);
      controller.abort();
      throw new Error('Request was cancelled');
    }
    options.signal.addEventListener('abort', () => controller.abort(), { once: true });
  }

  try {
    const response = await fetch(buildUrl(path, options?.params), {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: options?.body ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    });

    if (!response.ok) {
      let body: unknown;
      try { body = await response.json(); } catch { /* non-JSON body */ }
      throw new ApiError(
        `Request failed: ${response.status} ${response.statusText}`,
        response.status,
        body,
      );
    }

    // 204 No Content
    if (response.status === 204) return undefined as T;

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === 'AbortError') {
      if (options?.signal?.aborted) throw new Error('Request was cancelled');
      throw new TimeoutError();
    }
    throw new NetworkError(
      error instanceof Error ? error.message : 'Network request failed',
    );
  } finally {
    clearTimeout(timeoutId);
  }
}

// ── Public API ──

export const apiClient = {
  get<T>(path: string, params?: Record<string, string | number | boolean | undefined>, signal?: AbortSignal): Promise<T> {
    return executeRequest<T>('GET', path, { params, signal });
  },

  post<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
    return executeRequest<T>('POST', path, { body, signal });
  },

  put<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
    return executeRequest<T>('PUT', path, { body, signal });
  },

  delete<T>(path: string, signal?: AbortSignal): Promise<T> {
    return executeRequest<T>('DELETE', path, { signal });
  },
};
