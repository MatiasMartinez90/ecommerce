import type { MetadataRoute } from "next";
import { getStoreConfig } from "@/config/store";

export default function robots(): MetadataRoute.Robots {
  const { links } = getStoreConfig();
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/api/", "/carrito", "/checkout"] },
    sitemap: new URL("/sitemap.xml", links.storeUrl).toString(),
  };
}
