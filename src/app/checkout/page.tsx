"use client";

import type { FormEvent } from "react";
import { useRef, useState } from "react";
import Link from "next/link";
import { useCart } from "@/components/cart-provider";
import { formatMoney, useStore } from "@/components/store-provider";
import { commerceApi, paymentsApi } from "@/lib/commerce-client";
import type { Order, PaymentPreference } from "@/lib/commerce-types";

type PaymentMethod = "pay_at_store" | "mercado_pago";

export default function CheckoutPage() {
  const { cart, loading, reset } = useCart();
  const config = useStore();
  const idempotencyKey = useRef(crypto.randomUUID());
  const paymentIdempotencyKey = useRef(crypto.randomUUID());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [order, setOrder] = useState<Order | null>(null);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("pay_at_store");
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
          payment_method: paymentMethod,
          customer: {
            name: data.get("name"),
            email: data.get("email"),
            phone: data.get("phone"),
          },
          customer_notes: data.get("notes"),
        }),
      });
      if (paymentMethod === "mercado_pago") {
        try {
          const preference = await paymentsApi<PaymentPreference>(
            `shop-orders/${created.id}/preference`,
            {
              method: "POST",
              headers: { "idempotency-key": paymentIdempotencyKey.current },
              body: JSON.stringify({ cart_token: cart.token }),
            },
          );
          reset();
          window.location.assign(preference.checkout_url);
          return;
        } catch (cause) {
          setError(
            cause instanceof Error
              ? `El pedido quedó reservado, pero no pudimos abrir el pago: ${cause.message}`
              : "El pedido quedó reservado, pero no pudimos abrir el pago. Reintentá.",
          );
          return;
        }
      }
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
          <fieldset className="payment-options" disabled={submitting}>
            <legend>Forma de pago</legend>
            <label className={paymentMethod === "pay_at_store" ? "selected" : ""}>
              <input
                type="radio"
                name="payment_method"
                value="pay_at_store"
                checked={paymentMethod === "pay_at_store"}
                onChange={() => setPaymentMethod("pay_at_store")}
              />
              <span><strong>Pago en el local</strong><small>Abonás cuando retirás el pedido.</small></span>
            </label>
            <label className={paymentMethod === "mercado_pago" ? "selected" : ""}>
              <input
                type="radio"
                name="payment_method"
                value="mercado_pago"
                checked={paymentMethod === "mercado_pago"}
                onChange={() => setPaymentMethod("mercado_pago")}
              />
              <span><strong>Mercado Pago</strong><small>Pagás el total ahora en un checkout seguro.</small></span>
            </label>
          </fieldset>
          <button className="button" type="submit" disabled={submitting}>
            {submitting
              ? "Confirmando…"
              : paymentMethod === "mercado_pago"
                ? `Continuar a Mercado Pago · ${money(cart.subtotal)}`
                : `Confirmar pedido · ${money(cart.subtotal)}`}
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
