import { env } from "@/config/env";
import { getAccessToken } from "@/auth/tokenProvider";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code = "API_ERROR",
    readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function authenticatedFetch(path: string, init?: RequestInit) {
  const token = await getAccessToken();
  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      error?: { message?: string; code?: string; request_id?: string };
    } | null;
    throw new ApiError(
      payload?.error?.message ?? `Request failed with status ${response.status}`,
      response.status,
      payload?.error?.code,
      payload?.error?.request_id,
    );
  }

  return response;
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await authenticatedFetch(path, init);
  return response.json() as Promise<T>;
}

export async function apiDownload(path: string): Promise<Blob> {
  return (await authenticatedFetch(path)).blob();
}
