import type { Metadata } from "next";
import type { CSSProperties, ReactNode } from "react";
import { CartProvider } from "@/components/cart-provider";
import { ShopHeader } from "@/components/shop-header";
import { StoreProvider } from "@/components/store-provider";
import { getPublicStoreConfig, getStoreConfig } from "@/config/store";
import "./globals.css";

export function generateMetadata(): Metadata {
  const { brand } = getStoreConfig();
  return {
    title: { default: brand.name, template: `%s | ${brand.name}` },
    description: brand.description,
    metadataBase: new URL(getStoreConfig().links.storeUrl),
    alternates: { canonical: "/" },
    robots: { index: true, follow: true },
    openGraph: {
      title: brand.name,
      description: brand.description,
      type: "website",
    },
  };
}

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const config = getStoreConfig();
  const publicConfig = getPublicStoreConfig();
  const style = { "--accent": config.brand.accentColor } as CSSProperties;
  return (
    <html lang={config.locale.split("-")[0]} style={style}>
      <body>
        <StoreProvider value={publicConfig}>
          <CartProvider>
            <ShopHeader />
            {children}
            <footer className="footer">
              <div><strong>{config.brand.name}</strong><span>{config.pickup.label}</span></div>
              <div><span>{config.pickup.address}</span><a href={config.links.mainSite}>Sitio principal</a></div>
            </footer>
          </CartProvider>
        </StoreProvider>
      </body>
    </html>
  );
}
