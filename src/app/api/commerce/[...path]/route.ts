import { NextRequest, NextResponse } from "next/server";
import { getStoreConfig } from "@/config/store";

const ALLOWED_PATH =
  /^(categories|products(?:\/[a-z0-9-]+)?|carts(?:\/[A-Za-z0-9._~-]+(?:\/items\/[a-z0-9-]+)?)?|checkout)$/;
const ALLOWED_METHODS = new Set(["GET", "POST", "PUT", "DELETE"]);

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const method = request.method.toUpperCase();
  const path = (await context.params).path.join("/");
  if (!ALLOWED_METHODS.has(method) || !ALLOWED_PATH.test(path)) {
    return NextResponse.json({ detail: "Ruta inexistente" }, { status: 404 });
  }
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (!Number.isFinite(declaredLength) || declaredLength > 65_536) {
    return NextResponse.json({ detail: "Solicitud demasiado grande" }, { status: 413 });
  }
  const { integrations } = getStoreConfig();
  const target = new URL(`/v1/${path}`, integrations.commerceApiUrl);
  target.search = request.nextUrl.search;
  const headers = new Headers({ accept: "application/json" });
  const contentType = request.headers.get("content-type");
  const idempotencyKey = request.headers.get("idempotency-key");
  if (contentType) headers.set("content-type", contentType);
  if (idempotencyKey) headers.set("idempotency-key", idempotencyKey);
  const body = method === "GET" ? undefined : await request.arrayBuffer();
  if (body && body.byteLength > 65_536) {
    return NextResponse.json({ detail: "Solicitud demasiado grande" }, { status: 413 });
  }
  try {
    const response = await fetch(target, {
      method,
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json",
        "cache-control": "no-store",
      },
    });
  } catch {
    return NextResponse.json({ detail: "Servicio de comercio no disponible" }, { status: 503 });
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
