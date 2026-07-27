import Link from "next/link";
import { ProductCard } from "@/components/product-card";
import { getCategories, getProducts } from "@/lib/commerce";
import { getStoreConfig } from "@/config/store";

export const revalidate = 60;
export const dynamic = "force-dynamic";

export default async function Storefront({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; category?: string }>;
}) {
  const params = await searchParams;
  const query = params.q?.trim().slice(0, 80);
  const category = params.category?.trim().slice(0, 80);
  const [categories, products] = await Promise.all([
    getCategories(),
    getProducts({
      query: query && query.length >= 2 ? query : undefined,
      category,
      limit: 48,
    }),
  ]);
  const config = getStoreConfig();
  const schema = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: `${config.brand.name} Shop`,
    numberOfItems: products.total,
    itemListElement: products.items.map((product, index) => ({
      "@type": "ListItem",
      position: index + 1,
      url: new URL(`/productos/${product.slug}`, config.links.storeUrl).toString(),
      name: product.name,
    })),
  };

  return (
    <main>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema).replaceAll("<", "\\u003c") }}
      />
      <section className="hero">
        <p className="eyebrow">Selección profesional</p>
        <h1>Cuidá tu estilo<br /><em>todos los días.</em></h1>
        <p>{config.brand.description} Comprá online y retirá en {config.pickup.address}.</p>
      </section>

      <section className="catalog" aria-labelledby="catalog-title">
        <div className="catalog-tools">
          <div>
            <p className="eyebrow">Catálogo</p>
            <h2 id="catalog-title">
              {query
                ? `Resultados para “${query}”`
                : category
                  ? categories.find((item) => item.slug === category)?.name ?? "Productos"
                  : "Todos los productos"}
            </h2>
          </div>
          <form action="/" className="search" role="search">
            <label htmlFor="product-search">Buscar productos</label>
            <div>
              <input
                id="product-search"
                name="q"
                type="search"
                defaultValue={query}
                placeholder="Shampoo, pomada…"
                minLength={2}
                maxLength={80}
              />
              <button type="submit">Buscar</button>
            </div>
          </form>
        </div>
        <nav className="categories" aria-label="Categorías">
          <Link href="/" aria-current={!category ? "page" : undefined}>Todo</Link>
          {categories.map((item) => (
            <Link
              key={item.slug}
              href={`/?category=${encodeURIComponent(item.slug)}`}
              aria-current={category === item.slug ? "page" : undefined}
            >
              {item.name} <span>{item.product_count}</span>
            </Link>
          ))}
        </nav>
        {products.items.length ? (
          <div className="product-grid">
            {products.items.map((product) => <ProductCard key={product.slug} product={product} />)}
          </div>
        ) : (
          <div className="empty"><h2>No encontramos productos.</h2><Link href="/">Ver todo</Link></div>
        )}
      </section>
    </main>
  );
}
