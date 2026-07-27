import Link from "next/link";
import { AddToCart } from "@/components/add-to-cart";
import { getStoreConfig } from "@/config/store";
import type { Product } from "@/lib/commerce-types";

function mediaUrl(value: string | null): string | null {
  if (!value) return null;
  if (/^https:\/\//.test(value)) return value;
  return new URL(value.replace(/^\//, ""), `${getStoreConfig().links.mediaBaseUrl}/`).toString();
}

export function ProductCard({ product }: { product: Product }) {
  const config = getStoreConfig();
  const image = mediaUrl(product.image_url);
  const money = new Intl.NumberFormat(config.locale, {
    style: "currency",
    currency: config.currency,
    maximumFractionDigits: 0,
  }).format(product.price);
  return (
    <article className="product-card">
      <Link href={`/productos/${product.slug}`} className="product-media">
        {image ? (
          // Images are pre-sized variants served by the installation's media CDN.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={image} alt={product.name} width="640" height="720" loading="lazy" decoding="async" />
        ) : (
          <span aria-hidden="true">{product.name.slice(0, 2)}</span>
        )}
        {product.featured && <b>Destacado</b>}
      </Link>
      <div className="product-info">
        <div>
          <p className="eyebrow">{product.category_name ?? "Cuidado"}</p>
          <h2><Link href={`/productos/${product.slug}`}>{product.name}</Link></h2>
          <p>{product.short_description || product.description}</p>
        </div>
        <div className="product-buy"><strong>{money}</strong><AddToCart slug={product.slug} inStock={product.in_stock} compact /></div>
      </div>
    </article>
  );
}
