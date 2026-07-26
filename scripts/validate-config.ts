import { getStoreConfig } from "../src/config/store";

const config = getStoreConfig();
console.log(`Configuración válida: ${config.tenantId}`);
