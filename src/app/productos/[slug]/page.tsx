import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AddToCart } from "@/components/add-to-cart";
import { getStoreConfig } from "@/config/store";
import { getProduct } from "@/lib/commerce";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const product = await getProduct((await params).slug);
  if (!product) return { title: "Producto inexistente" };
  return {
    title: product.name,
    description: product.short_description || product.description,
    alternates: { canonical: `/productos/${product.slug}` },
  };
}

export default async function ProductPage({ params }: Props) {
  const product = await getProduct((await params).slug);
  if (!product) notFound();
  const config = getStoreConfig();
  const image = product.image_url
    ? /^https:\/\//.test(product.image_url)
      ? product.image_url
      : new URL(product.image_url.replace(/^\//, ""), `${config.links.mediaBaseUrl}/`).toString()
    : null;
  const money = new Intl.NumberFormat(config.locale, {
    style: "currency",
    currency: config.currency,
    maximumFractionDigits: 0,
  }).format(product.price);
  return (
    <main className="detail">
      <Link className="back" href="/">← Volver al catálogo</Link>
      <div className="detail-grid">
        <div className="detail-media">
          {image
            ? (
              // Product media is transformed and cached by the configured media CDN.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={image} alt={product.name} width="900" height="1000" decoding="async" />
            )
            : <span aria-hidden="true">{product.name.slice(0, 2)}</span>}
        </div>
        <article className="detail-info">
          <p className="eyebrow">{product.category_name ?? "Selección profesional"}</p>
          <h1>{product.name}</h1>
          <p className="detail-price">{money}</p>
          <p className="detail-copy">{product.description || product.short_description}</p>
          <dl>
            <div><dt>SKU</dt><dd>{product.sku}</dd></div>
            <div><dt>Disponibilidad</dt><dd>{product.in_stock ? "En stock" : "Sin stock"}</dd></div>
            <div><dt>Entrega</dt><dd>{config.pickup.label}</dd></div>
          </dl>
          <AddToCart slug={product.slug} inStock={product.in_stock} />
          <p className="pickup-note">Te avisamos cuando esté listo para retirar en {config.pickup.address}.</p>
        </article>
      </div>
    </main>
  );
}
