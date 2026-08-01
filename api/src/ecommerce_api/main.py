import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status

from .config import Settings, get_settings
from .database import Pool, create_pool
from .models import (
    CartCreateIn,
    CartItemSetIn,
    CartOut,
    CategoryCreateIn,
    CategoryOut,
    CategoryPatchIn,
    CheckoutIn,
    OrderOut,
    OrderStatusIn,
    PaymentCallbackIn,
    PaymentPreferenceIn,
    PaymentPreferenceOut,
    PaymentStatusOut,
    ProductCreateIn,
    ProductListOut,
    ProductOut,
    ProductPatchIn,
    StockAdjustIn,
)
from .payments import PaymentServiceUnavailable, create_payment_preference
from .repository import (
    CartNotFound,
    CommerceError,
    InvalidOrderTransition,
    StockConflict,
    adjust_stock,
    admin_categories,
    admin_order,
    admin_products,
    apply_payment_callback,
    attach_payment_preference,
    checkout,
    create_cart,
    create_category,
    create_product,
    get_cart,
    get_order_payment_status,
    get_product,
    list_categories,
    list_orders,
    list_products,
    order_for_cart,
    patch_category,
    patch_product,
    set_cart_item,
    transition_order,
)
from .security import InvalidSignature, sign_order, validate_callback_signature, verify_order


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.pool = await create_pool(settings)
    try:
        yield
    finally:
        await app.state.pool.close()


app = FastAPI(title="Ecommerce API", version="0.1.0", redoc_url=None, lifespan=lifespan)


def pool_for(request: Request) -> Pool:
    return request.app.state.pool


def settings_for(request: Request) -> Settings:
    return request.app.state.settings


async def require_api_key(
    settings: Annotated[Settings, Depends(settings_for)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="invalid API key")


def commerce_http_error(error: CommerceError) -> HTTPException:
    if isinstance(error, CartNotFound):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, (StockConflict, InvalidOrderTransition)):
        return HTTPException(status_code=409, detail=str(error))
    return HTTPException(status_code=422, detail=str(error))


@app.get("/health/live", tags=["health"])
async def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def ready(
    pool: Annotated[Pool, Depends(pool_for)],
    settings: Annotated[Settings, Depends(settings_for)],
) -> dict[str, str]:
    await pool.fetchval("SELECT 1")
    return {"status": "ok", "environment": settings.environment, "tenant": settings.tenant_id}


@app.get("/v1/categories", response_model=list[CategoryOut], tags=["catalog"])
async def categories(pool: Annotated[Pool, Depends(pool_for)]) -> list[dict]:
    return await list_categories(pool)


@app.get("/v1/products", response_model=ProductListOut, tags=["catalog"])
async def products(
    pool: Annotated[Pool, Depends(pool_for)],
    category: str | None = None,
    search: str | None = Query(default=None, max_length=100),
    featured: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return await list_products(
        pool, category=category, search=search, featured=featured, limit=limit, offset=offset
    )


@app.get("/v1/products/{slug}", response_model=ProductOut, tags=["catalog"])
async def product(slug: str, pool: Annotated[Pool, Depends(pool_for)]) -> dict:
    value = await get_product(pool, slug)
    if not value:
        raise HTTPException(status_code=404, detail="product not found")
    return value


@app.post("/v1/carts", response_model=CartOut, status_code=201, tags=["cart"])
async def new_cart(
    payload: CartCreateIn,
    pool: Annotated[Pool, Depends(pool_for)],
    settings: Annotated[Settings, Depends(settings_for)],
) -> dict:
    return await create_cart(pool, str(payload.customer_email) if payload.customer_email else None, settings.currency)


@app.get("/v1/carts/{token}", response_model=CartOut, tags=["cart"])
async def cart(token: str, pool: Annotated[Pool, Depends(pool_for)]) -> dict:
    try:
        return await get_cart(pool, token)
    except CommerceError as error:
        raise commerce_http_error(error) from error


@app.put("/v1/carts/{token}/items/{slug}", response_model=CartOut, tags=["cart"])
async def put_cart_item(
    token: str,
    slug: str,
    payload: CartItemSetIn,
    pool: Annotated[Pool, Depends(pool_for)],
) -> dict:
    try:
        return await set_cart_item(pool, token, slug, payload.quantity)
    except CommerceError as error:
        raise commerce_http_error(error) from error


@app.delete("/v1/carts/{token}/items/{slug}", response_model=CartOut, tags=["cart"])
async def delete_cart_item(token: str, slug: str, pool: Annotated[Pool, Depends(pool_for)]) -> dict:
    try:
        return await set_cart_item(pool, token, slug, 0)
    except CommerceError as error:
        raise commerce_http_error(error) from error


@app.post("/v1/checkout", response_model=OrderOut, status_code=201, tags=["orders"])
async def create_order(
    payload: CheckoutIn,
    pool: Annotated[Pool, Depends(pool_for)],
    settings: Annotated[Settings, Depends(settings_for)],
    response: Response,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=150)],
) -> dict:
    try:
        order, created = await checkout(
            pool,
            cart_token=payload.cart_token,
            idempotency_key=idempotency_key,
            customer_name=payload.customer.name,
            customer_email=str(payload.customer.email),
            customer_phone=payload.customer.phone,
            payment_method=payload.payment_method,
            customer_notes=payload.customer_notes,
            pickup_location=settings.pickup_location,
        )
        if not created:
            response.status_code = status.HTTP_200_OK
        return order
    except CommerceError as error:
        raise commerce_http_error(error) from error


@app.post(
    "/v1/shop-orders/{order_id}/preference",
    response_model=PaymentPreferenceOut,
    tags=["payments"],
)
async def payment_preference(
    order_id: UUID,
    payload: PaymentPreferenceIn,
    pool: Annotated[Pool, Depends(pool_for)],
    settings: Annotated[Settings, Depends(settings_for)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=150)],
) -> dict:
    try:
        order = await order_for_cart(pool, order_id, payload.cart_token)
        if order["payment_method"] != "mercado_pago":
            raise CommerceError("order does not use mercado pago")
        preference = await create_payment_preference(
            settings, order, idempotency_key=idempotency_key
        )
        expires_at = datetime.fromisoformat(preference["expires_at"])
        await attach_payment_preference(
            pool,
            order_id,
            checkout_url=preference["checkout_url"],
            provider_status_token=preference["status_token"],
            expires_at=expires_at,
            sandbox=preference["sandbox"],
        )
        return {**preference, "status_token": sign_order(order_id, settings.link_secret)}
    except CommerceError as error:
        raise commerce_http_error(error) from error
    except PaymentServiceUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/v1/payment-status/{token}", response_model=PaymentStatusOut, tags=["payments"])
async def payment_status(
    token: str,
    pool: Annotated[Pool, Depends(pool_for)],
    settings: Annotated[Settings, Depends(settings_for)],
) -> dict:
    try:
        order_id = verify_order(token, settings.link_secret)
        return {"purpose": "shop_order", **await get_order_payment_status(pool, order_id)}
    except (InvalidSignature, CommerceError) as error:
        raise HTTPException(status_code=404, detail="payment not found") from error


@app.post("/v1/payment-callback", status_code=204, tags=["payments"])
async def payment_callback(
    request: Request,
    pool: Annotated[Pool, Depends(pool_for)],
    settings: Annotated[Settings, Depends(settings_for)],
    timestamp: Annotated[str, Header(alias="X-Payment-Timestamp")],
    signature: Annotated[str, Header(alias="X-Payment-Signature")],
    event_id: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)],
) -> Response:
    body = await request.body()
    if len(body) > 65_536:
        raise HTTPException(status_code=413, detail="request too large")
    try:
        validate_callback_signature(
            body,
            timestamp,
            signature,
            settings.payments_callback_secret,
            max_skew_seconds=settings.callback_max_skew_seconds,
        )
        payload = PaymentCallbackIn.model_validate(json.loads(body))
        await apply_payment_callback(
            pool,
            provider_event_id=event_id,
            external_reference=payload.external_reference,
            provider_intent_id=payload.payment_intent_id,
            status=payload.status,
            amount=payload.amount,
            currency=payload.currency,
            payload_hash=hashlib.sha256(body).digest(),
        )
    except InvalidSignature as error:
        raise HTTPException(status_code=401, detail="invalid signature") from error
    except (ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=422, detail="invalid payload") from error
    except CommerceError as error:
        raise commerce_http_error(error) from error
    return Response(status_code=204)


@app.get(
    "/v1/admin/orders",
    dependencies=[Depends(require_api_key)],
    tags=["admin"],
)
async def admin_order_list(
    pool: Annotated[Pool, Depends(pool_for)],
    order_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    return await list_orders(pool, order_status, limit, offset)


@app.patch(
    "/v1/admin/orders/{order_id}/status",
    response_model=OrderOut,
    dependencies=[Depends(require_api_key)],
    tags=["admin"],
)
async def admin_order_status(
    order_id: UUID,
    payload: OrderStatusIn,
    pool: Annotated[Pool, Depends(pool_for)],
    actor: Annotated[str | None, Header(alias="X-Actor")] = None,
) -> dict:
    try:
        return await transition_order(pool, order_id, payload.status, payload.note, actor or "admin")
    except CommerceError as error:
        raise commerce_http_error(error) from error


@app.get(
    "/v1/admin/orders/{order_id}",
    response_model=OrderOut,
    dependencies=[Depends(require_api_key)],
    tags=["admin"],
)
async def admin_order_detail(order_id: UUID, pool: Annotated[Pool, Depends(pool_for)]) -> dict:
    try:
        return await admin_order(pool, order_id)
    except CommerceError as error:
        raise commerce_http_error(error) from error


@app.get(
    "/v1/admin/products",
    dependencies=[Depends(require_api_key)],
    tags=["admin"],
)
async def admin_product_list(pool: Annotated[Pool, Depends(pool_for)]) -> list[dict]:
    return await admin_products(pool)


@app.post("/v1/admin/products", dependencies=[Depends(require_api_key)], tags=["admin"])
async def admin_product_create(
    payload: ProductCreateIn,
    pool: Annotated[Pool, Depends(pool_for)],
) -> dict:
    try:
        return await create_product(pool, payload.model_dump())
    except CommerceError as error:
        raise commerce_http_error(error) from error


@app.patch(
    "/v1/admin/products/{product_id}",
    dependencies=[Depends(require_api_key)],
    tags=["admin"],
)
async def admin_product_patch(
    product_id: UUID,
    payload: ProductPatchIn,
    pool: Annotated[Pool, Depends(pool_for)],
) -> dict:
    try:
        return await patch_product(pool, product_id, payload.model_dump(exclude_unset=True))
    except CommerceError as error:
        raise commerce_http_error(error) from error


@app.post(
    "/v1/admin/products/{product_id}/stock",
    dependencies=[Depends(require_api_key)],
    tags=["admin"],
)
async def admin_stock(
    product_id: UUID,
    payload: StockAdjustIn,
    pool: Annotated[Pool, Depends(pool_for)],
    actor: Annotated[str | None, Header(alias="X-Actor")] = None,
) -> dict:
    try:
        return await adjust_stock(pool, product_id, payload.delta, payload.reason, actor or "admin")
    except CommerceError as error:
        raise commerce_http_error(error) from error


@app.get("/v1/admin/categories", dependencies=[Depends(require_api_key)], tags=["admin"])
async def admin_category_list(pool: Annotated[Pool, Depends(pool_for)]) -> list[dict]:
    return await admin_categories(pool)


@app.post("/v1/admin/categories", dependencies=[Depends(require_api_key)], tags=["admin"])
async def admin_category_create(
    payload: CategoryCreateIn,
    pool: Annotated[Pool, Depends(pool_for)],
) -> dict:
    try:
        return await create_category(pool, payload.model_dump())
    except CommerceError as error:
        raise commerce_http_error(error) from error


@app.patch(
    "/v1/admin/categories/{category_id}",
    dependencies=[Depends(require_api_key)],
    tags=["admin"],
)
async def admin_category_patch(
    category_id: UUID,
    payload: CategoryPatchIn,
    pool: Annotated[Pool, Depends(pool_for)],
) -> dict:
    try:
        return await patch_category(pool, category_id, payload.model_dump(exclude_unset=True))
    except CommerceError as error:
        raise commerce_http_error(error) from error
