"use client";

import { createContext, useContext } from "react";
import type { PublicStoreConfig } from "@/config/store";

const StoreContext = createContext<PublicStoreConfig | null>(null);

export function StoreProvider({
  value,
  children,
}: {
  value: PublicStoreConfig;
  children: React.ReactNode;
}) {
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): PublicStoreConfig {
  const value = useContext(StoreContext);
  if (!value) throw new Error("StoreProvider no está configurado");
  return value;
}

export function formatMoney(amount: number, locale: string, currency: string): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}
