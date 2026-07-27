import assert from "node:assert/strict";
import test from "node:test";
import example from "../config/store.example.json";
import {
  getPublicStoreConfig,
  getStoreConfig,
  type StoreConfig,
  validateStoreConfig,
} from "../src/config/store";

test("la configuración de ejemplo cumple el contrato", () => {
  const config = validateStoreConfig(example as StoreConfig);
  assert.equal(config.tenantId, "example-store");
  assert.equal(config.pickup.enabled, true);
});

test("rechaza tenants y monedas inválidos", () => {
  assert.throws(() => validateStoreConfig({
    ...(example as StoreConfig),
    tenantId: "../other",
  }));
  assert.throws(() => validateStoreConfig({
    ...(example as StoreConfig),
    currency: "pesos",
  }));
});

test("acepta configuración runtime sin exponer URLs internas al navegador", () => {
  process.env.STORE_CONFIG_JSON = JSON.stringify({
    ...example,
    tenantId: "runtime-store",
    integrations: {
      commerceApiUrl: "http://commerce.internal:8080",
      paymentsApiUrl: "http://payments.internal:8080",
    },
  });
  try {
    assert.equal(getStoreConfig().tenantId, "runtime-store");
    const publicConfig = getPublicStoreConfig();
    assert.equal(publicConfig.tenantId, "runtime-store");
    assert.equal("integrations" in publicConfig, false);
  } finally {
    delete process.env.STORE_CONFIG_JSON;
  }
});
