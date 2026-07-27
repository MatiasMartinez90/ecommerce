import defaultConfig from "../../config/store.example.json";

export interface StoreConfig {
  tenantId: string;
  brand: {
    name: string;
    shortName: string;
    description: string;
    accentColor: string;
  };
  locale: string;
  currency: string;
  pickup: {
    enabled: boolean;
    label: string;
    address: string;
  };
  links: {
    mainSite: string;
    storeUrl: string;
    mediaBaseUrl: string;
  };
  integrations: {
    commerceApiUrl: string;
    paymentsApiUrl: string;
  };
}

const TENANT_PATTERN = /^[a-z0-9][a-z0-9-]{1,62}$/;
const CURRENCY_PATTERN = /^[A-Z]{3}$/;
const HEX_COLOR_PATTERN = /^#[0-9a-f]{6}$/i;

export function validateStoreConfig(value: StoreConfig): StoreConfig {
  if (!TENANT_PATTERN.test(value.tenantId)) throw new Error("tenantId inválido");
  if (!value.brand.name.trim() || !value.brand.shortName.trim()) throw new Error("marca incompleta");
  if (!HEX_COLOR_PATTERN.test(value.brand.accentColor)) throw new Error("accentColor inválido");
  if (!CURRENCY_PATTERN.test(value.currency)) throw new Error("currency inválida");
  for (const candidate of [
    value.links.mainSite,
    value.links.storeUrl,
    value.links.mediaBaseUrl,
    value.integrations.commerceApiUrl,
    value.integrations.paymentsApiUrl,
  ]) {
    const url = new URL(candidate);
    if (!["http:", "https:"].includes(url.protocol)) throw new Error("URL inválida");
  }
  if (!value.pickup.enabled) throw new Error("esta versión requiere retiro en local");
  return value;
}

export function getStoreConfig(): StoreConfig {
  const serialized = process.env.STORE_CONFIG_JSON;
  if (!serialized) return validateStoreConfig(defaultConfig as StoreConfig);
  let value: unknown;
  try {
    value = JSON.parse(serialized);
  } catch {
    throw new Error("STORE_CONFIG_JSON no contiene JSON válido");
  }
  return validateStoreConfig(value as StoreConfig);
}

export type PublicStoreConfig = Omit<StoreConfig, "integrations">;

export function getPublicStoreConfig(): PublicStoreConfig {
  const value = getStoreConfig();
  return {
    tenantId: value.tenantId,
    brand: value.brand,
    locale: value.locale,
    currency: value.currency,
    pickup: value.pickup,
    links: value.links,
  };
}
