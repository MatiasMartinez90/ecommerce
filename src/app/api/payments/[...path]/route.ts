import { NextRequest, NextResponse } from "next/server";
import { getStoreConfig } from "@/config/store";

const ORDER_PAYMENT_PATH = /^shop-orders\/[0-9a-f-]{36}\/(preference|pay-at-store)$/i;
const STATUS_PATH = /^status\/[A-Za-z0-9._~-]{20,1000}$/;

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const method = request.method.toUpperCase();
  const path = (await context.params).path.join("/");
  const allowed =
    (method === "POST" && ORDER_PAYMENT_PATH.test(path)) ||
    (method === "GET" && STATUS_PATH.test(path));
  if (!allowed) {
    return NextResponse.json({ detail: "Ruta inexistente" }, { status: 404 });
  }
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (!Number.isFinite(declaredLength) || declaredLength > 65_536) {
    return NextResponse.json({ detail: "Solicitud demasiado grande" }, { status: 413 });
  }
  const { integrations } = getStoreConfig();
  const target = new URL(`/api/v1/payments/${path}`, integrations.commerceApiUrl);
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
    return NextResponse.json({ detail: "Servicio de pagos no disponible" }, { status: 503 });
  }
}

export const GET = proxy;
export const POST = proxy;
