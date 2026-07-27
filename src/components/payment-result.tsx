"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { paymentsApi } from "@/lib/commerce-client";
import type { PaymentStatus } from "@/lib/commerce-types";

const FINAL_STATUSES = new Set(["approved", "rejected", "cancelled", "refunded", "expired"]);

export function PaymentResult({ reference }: { reference: string }) {
  const [payment, setPayment] = useState<PaymentStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!reference) return;
    let cancelled = false;
    let attempts = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function refresh() {
      try {
        const value = await paymentsApi<PaymentStatus>(`status/${encodeURIComponent(reference)}`);
        if (cancelled) return;
        setPayment(value);
        setError("");
        attempts += 1;
        if (!FINAL_STATUSES.has(value.status) && attempts < 30) {
          timer = setTimeout(refresh, 2_000);
        }
      } catch (cause) {
        if (cancelled) return;
        setError(cause instanceof Error ? cause.message : "No pudimos consultar el pago.");
      }
    }
    void refresh();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [reference]);

  if (!reference) {
    return <Result title="Link inválido" detail="No encontramos una referencia de pago válida." />;
  }
  if (error) {
    return <Result title="No pudimos verificar el pago" detail={error} retry />;
  }
  if (!payment || payment.status === "pending" || payment.status === "created") {
    return (
      <Result
        title="Estamos verificando tu pago"
        detail="La confirmación puede tardar unos segundos. Esta pantalla se actualiza sola."
        pending
      />
    );
  }
  if (payment.status === "approved") {
    return <Result title="¡Pago aprobado!" detail="Tu pedido quedó confirmado y ya estamos preparándolo." />;
  }
  if (payment.status === "refunded") {
    return <Result title="Pago reintegrado" detail="El importe fue marcado como reintegrado." />;
  }
  return (
    <Result
      title="El pago no se completó"
      detail="Podés volver al shop y elegir pagar nuevamente o hacerlo en el local."
    />
  );
}

function Result({
  title,
  detail,
  pending = false,
  retry = false,
}: {
  title: string;
  detail: string;
  pending?: boolean;
  retry?: boolean;
}) {
  return (
    <main className="page">
      <section className="confirmation" aria-live="polite">
        <span aria-hidden="true">{pending ? "…" : "✓"}</span>
        <p className="eyebrow">Estado del pago</p>
        <h1>{title}</h1>
        <p>{detail}</p>
        {retry && <button className="button" onClick={() => window.location.reload()}>Reintentar</button>}
        {!retry && <Link className="button" href="/">Volver al shop</Link>}
      </section>
    </main>
  );
}
