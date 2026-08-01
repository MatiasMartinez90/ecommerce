from datetime import UTC, datetime, timedelta

import httpx

from .config import Settings


class PaymentServiceUnavailable(RuntimeError):
    pass


async def create_payment_preference(
    settings: Settings,
    order: dict,
    *,
    idempotency_key: str,
) -> dict:
    if not settings.payments_url:
        raise PaymentServiceUnavailable("payment service is not configured")

    result_url = f"{settings.storefront_url.rstrip('/')}/pago/resultado"
    payload = {
        "tenant_id": settings.tenant_id,
        "external_reference": f"ecommerce:order:{order['id']}",
        "amount": order["total"],
        "currency": order["currency"],
        "description": f"Pedido #{order['order_number']}",
        "payer_email": order["customer_email"],
        "items": [
            {
                "reference": item["sku"],
                "title": item["product_name"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
            }
            for item in order["items"]
        ],
        "success_url": result_url,
        "pending_url": result_url,
        "failure_url": result_url,
        "callback_url": f"{settings.public_url.rstrip('/')}/v1/payment-callback",
        "expires_at": (datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
        "metadata": {"order_id": str(order["id"]), "kind": "shop_order"},
    }
    headers = {
        "X-API-Key": settings.payments_api_key,
        "Idempotency-Key": idempotency_key,
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(12, connect=3)) as client:
            response = await client.post(
                f"{settings.payments_url.rstrip('/')}/v1/payment-intents",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise PaymentServiceUnavailable("payment service request failed") from error
