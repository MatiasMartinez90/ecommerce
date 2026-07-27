export class CommerceError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function apiRequest<T>(basePath: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${basePath}/${path.replace(/^\//, "")}`, {
    ...init,
    cache: "no-store",
    headers: {
      accept: "application/json",
      ...(init?.body ? { "content-type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload && typeof payload.detail === "string" ? payload.detail : null;
    throw new CommerceError(detail ?? "No pudimos completar la operación.", response.status);
  }
  return payload as T;
}

export async function commerceApi<T>(path: string, init?: RequestInit): Promise<T> {
  return apiRequest<T>("/api/commerce", path, init);
}

export async function paymentsApi<T>(path: string, init?: RequestInit): Promise<T> {
  return apiRequest<T>("/api/payments", path, init);
}
