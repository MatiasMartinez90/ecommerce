export class CommerceError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

export async function commerceApi<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/commerce/${path.replace(/^\//, "")}`, {
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
