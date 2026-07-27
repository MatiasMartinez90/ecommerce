"use client";

import type { FormEvent } from "react";
import { useRef, useState } from "react";
import Link from "next/link";
import { useCart } from "@/components/cart-provider";
import { formatMoney, useStore } from "@/components/store-provider";
import { commerceApi } from "@/lib/commerce-client";
import type { Order } from "@/lib/commerce-types";

export default function CheckoutPage() {
  const { cart, loading, reset } = useCart();
  const config = useStore();
  const idempotencyKey = useRef(crypto.randomUUID());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [order, setOrder] = useState<Order | null>(null);
  const money = (value: number) => formatMoney(value, config.locale, config.currency);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!cart?.items.length) return;
    setSubmitting(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const created = await commerceApi<Order>("checkout", {
        method: "POST",
        headers: { "idempotency-key": idempotencyKey.current },
        body: JSON.stringify({
          cart_token: cart.token,
          payment_method: "pay_at_store",
          customer: {
            name: data.get("name"),
            email: data.get("email"),
            phone: data.get("phone"),
          },
          customer_notes: data.get("notes"),
        }),
      });
      setOrder(created);
      reset();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No pudimos confirmar el pedido.");
    } finally {
      setSubmitting(false);
    }
  }

  if (order) {
    return (
      <main className="page">
        <section className="confirmation">
          <span aria-hidden="true">✓</span>
          <p className="eyebrow">Pedido #{String(order.order_number).padStart(6, "0")}</p>
          <h1>¡Listo, {order.customer_name.split(" ")[0]}!</h1>
          <p>Recibimos tu pedido. Te avisaremos cuando esté listo para retirar.</p>
          <dl>
            <div><dt>Total</dt><dd>{money(order.total)}</dd></div>
            <div><dt>Pago</dt><dd>En el local</dd></div>
            <div><dt>Retiro</dt><dd>{order.pickup_location}</dd></div>
          </dl>
          <Link className="button" href="/">Volver al shop</Link>
        </section>
      </main>
    );
  }
  if (loading) return <main className="page"><div className="loading" /></main>;
  if (!cart?.items.length) {
    return <main className="page"><div className="empty"><h1>No hay productos para confirmar.</h1><Link className="button" href="/">Volver</Link></div></main>;
  }
  return (
    <main className="page">
      <div className="page-heading"><div><p className="eyebrow">{config.pickup.label}</p><h1>Confirmá tu pedido</h1></div></div>
      {error && <p className="alert" role="alert">{error}</p>}
      <div className="checkout-layout">
        <form className="checkout-form" onSubmit={submit}>
          <fieldset disabled={submitting}>
            <legend>Datos de contacto</legend>
            <label>Nombre y apellido<input name="name" autoComplete="name" required minLength={2} maxLength={120} /></label>
            <div className="form-row">
              <label>Email<input name="email" type="email" autoComplete="email" required /></label>
              <label>Teléfono<input name="phone" type="tel" autoComplete="tel" required minLength={7} maxLength={21} /></label>
            </div>
            <label>Notas <small>(opcional)</small><textarea name="notes" rows={4} maxLength={1000} /></label>
          </fieldset>
          <div className="payment-note"><strong>Pago en el local</strong><span>Abonás cuando retirás el pedido.</span></div>
          <button className="button" type="submit" disabled={submitting}>
            {submitting ? "Confirmando…" : `Confirmar pedido · ${money(cart.subtotal)}`}
          </button>
        </form>
        <aside className="summary">
          <p className="eyebrow">Tu pedido</p>
          {cart.items.map((item) => <div key={item.product.slug}><span>{item.quantity} × {item.product.name}</span><strong>{money(item.line_total)}</strong></div>)}
          <div className="summary-total"><span>Total</span><strong>{money(cart.subtotal)}</strong></div>
          <p>Retiro en {config.pickup.address}</p>
        </aside>
      </div>
    </main>
  );
}
