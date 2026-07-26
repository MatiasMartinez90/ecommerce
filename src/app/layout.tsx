import type { Metadata } from "next";
import type { CSSProperties, ReactNode } from "react";
import { getStoreConfig } from "@/config/store";
import "./globals.css";

export function generateMetadata(): Metadata {
  const { brand } = getStoreConfig();
  return {
    title: { default: brand.name, template: `%s | ${brand.name}` },
    description: brand.description,
    robots: { index: false, follow: false },
  };
}

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const config = getStoreConfig();
  const style = { "--accent": config.brand.accentColor } as CSSProperties;
  return (
    <html lang={config.locale.split("-")[0]} style={style}>
      <body>{children}</body>
    </html>
  );
}
