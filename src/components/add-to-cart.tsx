"use client";

import { useState } from "react";
import { useCart } from "@/components/cart-provider";

export function AddToCart({
  slug,
  inStock,
  compact = false,
}: {
  slug: string;
  inStock: boolean;
  compact?: boolean;
}) {
  const { add, busy } = useCart();
  const [added, setAdded] = useState(false);
  async function handleAdd() {
    try {
      await add(slug);
      setAdded(true);
      window.setTimeout(() => setAdded(false), 1400);
    } catch {
      // CartProvider exposes the actionable message.
    }
  }
  return (
    <button
      className={`button${compact ? " button-compact" : ""}`}
      type="button"
      disabled={!inStock || busy}
      onClick={handleAdd}
      aria-live="polite"
    >
      {!inStock ? "Sin stock" : added ? "Agregado ✓" : "Agregar"}
    </button>
  );
}
