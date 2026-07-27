import type { MetadataRoute } from "next";
import { getProducts } from "@/lib/commerce";
import { getStoreConfig } from "@/config/store";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const { links } = getStoreConfig();
  const products = await getProducts({ limit: 100 });
  return [
    { url: links.storeUrl, changeFrequency: "daily", priority: 1 },
    ...products.items.map((product) => ({
      url: new URL(`/productos/${product.slug}`, links.storeUrl).toString(),
      changeFrequency: "weekly" as const,
      priority: 0.8,
    })),
  ];
}
