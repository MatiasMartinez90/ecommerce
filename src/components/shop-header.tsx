"use client";

import Link from "next/link";
import { useCart } from "@/components/cart-provider";
import { useStore } from "@/components/store-provider";

export function ShopHeader() {
  const { brand, links } = useStore();
  const { cart, loading } = useCart();
  const count = cart?.total_quantity ?? 0;
  return (
    <header className="header">
      <Link className="brand" href="/" aria-label={`${brand.name}, inicio`}>
        {brand.shortName}<small>SHOP</small>
      </Link>
      <nav aria-label="Navegación principal">
        <Link href="/">Productos</Link>
        <a href={links.mainSite}>Sitio principal</a>
        <Link className="cart-link" href="/carrito" aria-label={`Carrito, ${count} productos`}>
          <span aria-hidden="true">▱</span> {loading ? "·" : count}
        </Link>
      </nav>
    </header>
  );
}
