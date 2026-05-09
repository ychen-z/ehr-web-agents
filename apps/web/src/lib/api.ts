import { parseApiError, ApiError } from "./errors";

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

let _getToken: (() => string | null) | null = null;

export function setTokenProvider(fn: () => string | null) {
  _getToken = fn;
}

function getToken(): string | null {
  return _getToken?.() ?? null;
}

export interface RequestOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string | number | undefined>;
  headers?: Record<string, string>;
  noAuth?: boolean;
  signal?: AbortSignal;
}

function isEmptyResponse(response: Response): boolean {
  if (response.status === 204) return true;
  const cl = response.headers.get("content-length");
  if (cl === "0") return true;
  return false;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = buildUrl(path, options.params);
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (!options.noAuth) {
    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const response = await fetch(url, {
    method: options.method ?? "GET",
    headers,
    body: options.body != null ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  if (isEmptyResponse(response)) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function buildUrl(path: string, params?: Record<string, string | number | undefined>): string {
  const url = new URL(path, API_BASE_URL);

  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    }
  }

  return url.toString();
}

const api = {
  get<T>(path: string, options?: Omit<RequestOptions, "method" | "body">) {
    return request<T>(path, { ...options, method: "GET" });
  },
  post<T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) {
    return request<T>(path, { ...options, method: "POST", body });
  },
  put<T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) {
    return request<T>(path, { ...options, method: "PUT", body });
  },
  patch<T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) {
    return request<T>(path, { ...options, method: "PATCH", body });
  },
  delete<T>(path: string, options?: Omit<RequestOptions, "method">) {
    return request<T>(path, { ...options, method: "DELETE" });
  },
};

export { api, request, ApiError };
