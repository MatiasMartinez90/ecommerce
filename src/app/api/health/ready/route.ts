import { NextResponse } from "next/server";
import { getStoreConfig } from "@/config/store";

export async function GET() {
  try {
    const config = getStoreConfig();
    const target = new URL("/v1/categories", config.integrations.commerceApiUrl);
    const response = await fetch(target, {
      headers: { accept: "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(3_000),
    });
    if (!response.ok) throw new Error("commerce unavailable");
    return NextResponse.json(
      { status: "ok", tenant: config.tenantId },
      { headers: { "cache-control": "no-store" } },
    );
  } catch {
    return NextResponse.json(
      { status: "unavailable" },
      { status: 503, headers: { "cache-control": "no-store" } },
    );
  }
}
