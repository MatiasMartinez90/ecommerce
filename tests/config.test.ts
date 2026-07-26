import assert from "node:assert/strict";
import test from "node:test";
import example from "../config/store.example.json";
import { type StoreConfig, validateStoreConfig } from "../src/config/store";

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
