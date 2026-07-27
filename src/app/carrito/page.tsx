"use client";

import Link from "next/link";
import { useCart } from "@/components/cart-provider";
import { formatMoney, useStore } from "@/components/store-provider";

export default function CartPage() {
  const { cart, loading, busy, error, setQuantity, remove } = useCart();
  const config = useStore();
  const money = (value: number) => formatMoney(value, config.locale, config.currency);
  if (loading) return <main className="page"><div className="loading" aria-label="Cargando carrito" /></main>;
  if (!cart?.items.length) {
    return (
      <main className="page">
        <div className="empty">
          <p className="eyebrow">Tu carrito</p><h1>Todavía está vacío.</h1>
          <p>Elegí productos del catálogo y volvé cuando quieras.</p>
          <Link className="button" href="/">Ver productos</Link>
        </div>
      </main>
    );
  }
  return (
    <main className="page">
      <div className="page-heading">
        <div><p className="eyebrow">Tu selección</p><h1>Carrito</h1></div>
        <span>{cart.total_quantity} productos</span>
      </div>
      {error && <p className="alert" role="alert">{error}</p>}
      <div className="cart-layout">
        <section className="cart-items" aria-label="Productos del carrito">
          {cart.items.map((item) => (
            <article className="cart-item" key={item.product.slug}>
              <div><p className="eyebrow">{item.product.category_name ?? "Producto"}</p><h2>{item.product.name}</h2>
                <button type="button" disabled={busy} onClick={() => void remove(item.product.slug)}>Eliminar</button>
              </div>
              <div className="quantity" aria-label={`Cantidad de ${item.product.name}`}>
                <button type="button" disabled={busy} onClick={() => void setQuantity(item.product.slug, item.quantity - 1)}>−</button>
                <span>{item.quantity}</span>
                <button
                  type="button"
                  disabled={busy || item.quantity >= item.product.available_qty}
                  onClick={() => void setQuantity(item.product.slug, item.quantity + 1)}
                >+</button>
              </div>
              <strong>{money(item.line_total)}</strong>
            </article>
          ))}
        </section>
        <aside className="summary">
          <p className="eyebrow">Resumen</p>
          <div><span>Subtotal</span><strong>{money(cart.subtotal)}</strong></div>
          <div><span>Entrega</span><strong>Retiro gratis</strong></div>
          <div className="summary-total"><span>Total</span><strong>{money(cart.subtotal)}</strong></div>
          <Link className="button" href="/checkout">Continuar compra</Link>
        </aside>
      </div>
    </main>
  );
}
