import "server-only";

import { getStoreConfig } from "@/config/store";
import type { Category, Product, ProductList } from "@/lib/commerce-types";

async function commerceFetch<T>(
  path: string,
  options: { tags?: string[]; revalidate?: number } = {},
): Promise<T> {
  const { integrations } = getStoreConfig();
  const url = new URL(`/v1/${path.replace(/^\//, "")}`, integrations.commerceApiUrl);
  const response = await fetch(url, {
    headers: { accept: "application/json" },
    next: { revalidate: options.revalidate ?? 60, tags: options.tags },
  });
  if (!response.ok) throw new Error(`commerce_api_${response.status}`);
  return response.json() as Promise<T>;
}

export function getCategories(): Promise<Category[]> {
  return commerceFetch("categories", { tags: ["categories"], revalidate: 300 });
}

export function getProducts(params: {
  category?: string;
  query?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<ProductList> {
  const search = new URLSearchParams({
    limit: String(params.limit ?? 48),
    offset: String(params.offset ?? 0),
  });
  if (params.category) search.set("category", params.category);
  if (params.query) search.set("search", params.query);
  return commerceFetch(`products?${search}`, { tags: ["products"], revalidate: 60 });
}

export async function getProduct(slug: string): Promise<Product | null> {
  try {
    return await commerceFetch(`products/${encodeURIComponent(slug)}`, {
      tags: ["products", `product-${slug}`],
      revalidate: 60,
    });
  } catch (error) {
    if (error instanceof Error && error.message === "commerce_api_404") return null;
    throw error;
  }
}
