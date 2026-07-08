const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  code: string;
  index: number | null;

  constructor(status: number, code: string, message: string, index: number | null) {
    super(message);
    this.status = status;
    this.code = code;
    this.index = index;
  }
}

type ErrorBody = {
  error?: { code: string; message: string; index: number | null };
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const errorBody = body as ErrorBody | null;
    throw new ApiError(
      response.status,
      errorBody?.error?.code ?? "UNKNOWN",
      errorBody?.error?.message ?? "エラーが発生しました",
      errorBody?.error?.index ?? null,
    );
  }

  return body as T;
}

function authHeader(token?: string): HeadersInit | undefined {
  return token ? { Authorization: `Bearer ${token}` } : undefined;
}

export function get<T>(path: string, token?: string): Promise<T> {
  return request<T>(path, { method: "GET", headers: authHeader(token) });
}

export function post<T>(path: string, body?: unknown, token?: string): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: authHeader(token),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function put<T>(path: string, body?: unknown, token?: string): Promise<T> {
  return request<T>(path, {
    method: "PUT",
    headers: authHeader(token),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function del<T>(path: string, token?: string): Promise<T> {
  return request<T>(path, { method: "DELETE", headers: authHeader(token) });
}

export function extractMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}
