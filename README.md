# ecommerce

Aplicación de comercio electrónico reutilizable, configurable por tenant y
desacoplada del sitio que la consume.

Esta entrega incluye storefront responsive, catálogo y detalle renderizados en
servidor, búsqueda/filtros, carrito persistente y checkout idempotente con
retiro y pago en el local. El navegador usa un BFF same-origin con rutas,
tamaño y timeout limitados; las URLs internas no se publican en el bundle.

La administración de inventario y la integración con el servicio independiente
`mercadopago` se incorporan en entregas posteriores del roadmap.

La rama de integración es `dev`. Ningún workflow despliega producción desde
esta rama.

## Configuración

La instalación se define con `STORE_CONFIG_JSON`. El contrato completo y
valores de desarrollo están en `config/store.example.json`; incluye marca,
locale, moneda, retiro, URLs públicas, CDN de medios y endpoints internos.

```bash
export STORE_CONFIG_JSON="$(jq -c . config/store.example.json)"
npm run build
npm run start
```

La configuración se valida al usarla y las integraciones se eliminan antes de
hidratar componentes cliente. El catálogo estable usa caché con
revalidación; carrito y checkout siempre usan `no-store`.

## Operación

- `GET /api/health/live`: vida del proceso.
- `GET /api/health/ready`: valida configuración y acceso al API de comercio.
- `GET /robots.txt` y `GET /sitemap.xml`: SEO por instalación.
- La imagen corre como UID/GID `10001` y usa el output standalone de Next.js.

## Verificación

```bash
npm ci
npm audit --omit=dev --audit-level=high
npm run config:validate
npm test
npm run lint
npm run build
```
