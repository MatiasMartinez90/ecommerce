import hashlib
import json
import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import asyncpg

from .database import Pool, transaction
from .security import hash_token


class CommerceError(RuntimeError):
    pass


class CartNotFound(CommerceError):
    pass


class CartUnavailable(CommerceError):
    pass


class ProductUnavailable(CommerceError):
    pass


class StockConflict(CommerceError):
    pass


class InvalidOrderTransition(CommerceError):
    pass


PRODUCT_COLUMNS = """
p.id, p.slug, p.name, p.sku, p.description, p.short_description,
       c.slug AS category_slug, c.name AS category_name,
       p.image_url, p.gallery, p.price, p.qty AS available_qty,
       p.qty > 0 AS in_stock, p.featured
"""

PRODUCT_SELECT = f"""
SELECT {PRODUCT_COLUMNS}
FROM products p
LEFT JOIN product_categories c ON c.id = p.category_id
"""


def _product(row: asyncpg.Record | dict) -> dict[str, Any]:
    value = dict(row)
    gallery = value.get("gallery")
    if isinstance(gallery, str):
        gallery = json.loads(gallery)
    value["gallery"] = list(gallery or [])
    return value


async def list_categories(pool: Pool) -> list[dict]:
    rows = await pool.fetch(
        """
        SELECT c.slug, c.name, c.description, count(p.id)::int AS product_count
        FROM product_categories c
        LEFT JOIN products p ON p.category_id = c.id AND p.active
        WHERE c.active
        GROUP BY c.id
        ORDER BY c.sort_order, c.name
        """
    )
    return [dict(row) for row in rows]


async def list_products(
    pool: Pool,
    *,
    category: str | None,
    search: str | None,
    featured: bool | None,
    limit: int,
    offset: int,
) -> dict:
    clauses = ["p.active"]
    values: list[Any] = []
    if category:
        values.append(category)
        clauses.append(f"c.slug = ${len(values)}")
    if search:
        values.append(f"%{search.strip()}%")
        clauses.append(
            f"(p.name ILIKE ${len(values)} OR p.description ILIKE ${len(values)} "
            f"OR p.sku ILIKE ${len(values)})"
        )
    if featured is not None:
        values.append(featured)
        clauses.append(f"p.featured = ${len(values)}")
    where = " AND ".join(clauses)
    total = await pool.fetchval(
        f"SELECT count(*) FROM products p LEFT JOIN product_categories c ON c.id=p.category_id WHERE {where}",
        *values,
    )
    values.extend([limit, offset])
    rows = await pool.fetch(
        f"""
        {PRODUCT_SELECT}
        WHERE {where}
        ORDER BY p.featured DESC, p.sort_order, p.name
        LIMIT ${len(values) - 1} OFFSET ${len(values)}
        """,
        *values,
    )
    return {"items": [_product(row) for row in rows], "total": total, "limit": limit, "offset": offset}


async def get_product(pool: Pool, slug: str) -> dict | None:
    row = await pool.fetchrow(f"{PRODUCT_SELECT} WHERE p.slug=$1 AND p.active", slug)
    return _product(row) if row else None


async def _cart_row(connection: asyncpg.Connection | Pool, token: str, *, lock: bool = False):
    suffix = " FOR UPDATE" if lock else ""
    return await connection.fetchrow(
        f"SELECT * FROM shopping_carts WHERE token_hash=$1{suffix}", hash_token(token)
    )


async def _render_cart(connection: asyncpg.Connection | Pool, row, token: str) -> dict:
    items = await connection.fetch(
        f"""
        SELECT {PRODUCT_COLUMNS}, ci.quantity,
               ci.quantity * p.price AS line_total
        FROM shopping_cart_items ci
        JOIN products p ON p.id=ci.product_id
        LEFT JOIN product_categories c ON c.id=p.category_id
        WHERE ci.cart_id=$1
        ORDER BY p.sort_order, p.name
        """,
        row["id"],
    )
    rendered = []
    for item in items:
        value = dict(item)
        quantity = value.pop("quantity")
        line_total = value.pop("line_total")
        rendered.append({"product": _product(value), "quantity": quantity, "line_total": line_total})
    return {
        "token": token,
        "status": row["status"],
        "currency": row["currency"].strip(),
        "items": rendered,
        "subtotal": sum(item["line_total"] for item in rendered),
        "total_quantity": sum(item["quantity"] for item in rendered),
        "expires_at": row["expires_at"],
    }


async def create_cart(pool: Pool, customer_email: str | None, currency: str) -> dict:
    token = secrets.token_urlsafe(32)
    row = await pool.fetchrow(
        """
        INSERT INTO shopping_carts (token_hash, customer_email, currency)
        VALUES ($1,$2,$3) RETURNING *
        """,
        hash_token(token),
        customer_email.lower() if customer_email else None,
        currency,
    )
    return await _render_cart(pool, row, token)


async def get_cart(pool: Pool, token: str) -> dict:
    row = await _cart_row(pool, token)
    if not row:
        raise CartNotFound("cart not found")
    if row["status"] == "active" and row["expires_at"] <= datetime.now(UTC):
        await pool.execute(
            "UPDATE shopping_carts SET status='expired',updated_at=now() WHERE id=$1", row["id"]
        )
        row = dict(row)
        row["status"] = "expired"
    return await _render_cart(pool, row, token)


async def set_cart_item(pool: Pool, token: str, slug: str, quantity: int) -> dict:
    async with transaction(pool) as connection:
        cart = await _cart_row(connection, token, lock=True)
        if not cart:
            raise CartNotFound("cart not found")
        if cart["status"] != "active" or cart["expires_at"] <= datetime.now(UTC):
            raise CartUnavailable("cart is unavailable")
        product = await connection.fetchrow(
            "SELECT id,qty FROM products WHERE slug=$1 AND active FOR UPDATE", slug
        )
        if not product:
            raise ProductUnavailable("product is unavailable")
        if quantity <= 0:
            await connection.execute(
                "DELETE FROM shopping_cart_items WHERE cart_id=$1 AND product_id=$2",
                cart["id"],
                product["id"],
            )
        else:
            if product["qty"] < quantity:
                raise StockConflict("insufficient stock")
            await connection.execute(
                """
                INSERT INTO shopping_cart_items (cart_id,product_id,quantity)
                VALUES ($1,$2,$3)
                ON CONFLICT (cart_id,product_id) DO UPDATE
                SET quantity=EXCLUDED.quantity,updated_at=now()
                """,
                cart["id"],
                product["id"],
                quantity,
            )
        cart = await connection.fetchrow(
            "UPDATE shopping_carts SET last_activity=now(),updated_at=now() WHERE id=$1 RETURNING *",
            cart["id"],
        )
        return await _render_cart(connection, cart, token)


async def _load_order(connection: asyncpg.Connection | Pool, order_id: UUID) -> dict:
    order = await connection.fetchrow("SELECT * FROM shop_orders WHERE id=$1", order_id)
    if not order:
        raise CommerceError("order not found")
    items = await connection.fetch(
        """
        SELECT product_slug,product_name,sku,unit_price,quantity,line_total
        FROM shop_order_items WHERE order_id=$1 ORDER BY id
        """,
        order_id,
    )
    value = dict(order)
    value["currency"] = value["currency"].strip()
    value["items"] = [dict(item) for item in items]
    return value


async def checkout(
    pool: Pool,
    *,
    cart_token: str,
    idempotency_key: str,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    payment_method: str,
    customer_notes: str,
    pickup_location: str,
) -> tuple[dict, bool]:
    idempotency_hash = hashlib.sha256(idempotency_key.encode()).digest()
    async with transaction(pool) as connection:
        await connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended($1,0))", idempotency_key
        )
        existing = await connection.fetchrow(
            """
            SELECT o.id,c.token_hash=$2 AS same_cart
            FROM shop_orders o JOIN shopping_carts c ON c.id=o.cart_id
            WHERE o.idempotency_hash=$1
            """,
            idempotency_hash,
            hash_token(cart_token),
        )
        if existing:
            if not existing["same_cart"]:
                raise CommerceError("idempotency key belongs to another cart")
            return await _load_order(connection, existing["id"]), False
        cart = await _cart_row(connection, cart_token, lock=True)
        if not cart:
            raise CartNotFound("cart not found")
        if cart["status"] != "active" or cart["expires_at"] <= datetime.now(UTC):
            raise CartUnavailable("cart is unavailable")
        rows = await connection.fetch(
            """
            SELECT p.id,p.slug,p.name,p.sku,p.price,p.qty,ci.quantity
            FROM shopping_cart_items ci JOIN products p ON p.id=ci.product_id
            WHERE ci.cart_id=$1 AND p.active ORDER BY p.id FOR UPDATE OF p
            """,
            cart["id"],
        )
        if not rows:
            raise CartUnavailable("cart is empty")
        for row in rows:
            if row["qty"] < row["quantity"]:
                raise StockConflict(f"insufficient stock for {row['name']}")
        subtotal = sum(row["price"] * row["quantity"] for row in rows)
        status = "pending" if payment_method == "mercado_pago" else "confirmed"
        payment_status = "pending" if payment_method == "mercado_pago" else "unpaid"
        order = await connection.fetchrow(
            """
            INSERT INTO shop_orders (
                cart_id,idempotency_hash,customer_name,customer_email,customer_phone,
                status,payment_method,payment_status,currency,subtotal,total,
                pickup_location,customer_notes
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$10,$11,$12)
            RETURNING id,order_number
            """,
            cart["id"],
            idempotency_hash,
            customer_name,
            customer_email.lower(),
            customer_phone,
            status,
            payment_method,
            payment_status,
            cart["currency"],
            subtotal,
            pickup_location,
            customer_notes,
        )
        for row in rows:
            updated = await connection.fetchval(
                "UPDATE products SET qty=qty-$2,updated_at=now() WHERE id=$1 AND qty >= $2 RETURNING qty",
                row["id"],
                row["quantity"],
            )
            if updated is None:
                raise StockConflict(f"insufficient stock for {row['name']}")
            await connection.execute(
                """
                INSERT INTO shop_order_items (
                    order_id,product_id,product_slug,product_name,sku,unit_price,quantity,line_total
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                """,
                order["id"],
                row["id"],
                row["slug"],
                row["name"],
                row["sku"],
                row["price"],
                row["quantity"],
                row["price"] * row["quantity"],
            )
            await connection.execute(
                "INSERT INTO stock_movements (product_id,delta,reason,created_by) VALUES ($1,$2,$3,'checkout')",
                row["id"],
                -row["quantity"],
                f"order {order['order_number']}",
            )
        await connection.execute(
            """
            UPDATE shopping_carts SET status='converted',converted_at=now(),updated_at=now(),
                customer_email=$2 WHERE id=$1
            """,
            cart["id"],
            customer_email.lower(),
        )
        await connection.execute(
            """
            INSERT INTO shop_order_status_history (order_id,from_status,to_status,note,actor)
            VALUES ($1,NULL,$2,'checkout','storefront')
            """,
            order["id"],
            status,
        )
        return await _load_order(connection, order["id"]), True


async def order_for_cart(pool: Pool, order_id: UUID, cart_token: str) -> dict:
    row = await pool.fetchrow(
        """
        SELECT o.* FROM shop_orders o JOIN shopping_carts c ON c.id=o.cart_id
        WHERE o.id=$1 AND c.token_hash=$2
        """,
        order_id,
        hash_token(cart_token),
    )
    if not row:
        raise CommerceError("order not found")
    return await _load_order(pool, row["id"])


async def get_order(pool: Pool, order_id: UUID) -> dict:
    return await _load_order(pool, order_id)


async def get_order_payment_status(pool: Pool, order_id: UUID) -> dict:
    row = await pool.fetchrow(
        """
        SELECT payment_status AS status,total AS amount,currency,
               COALESCE(payment_expires_at, created_at + interval '30 minutes') AS expires_at,
               payment_sandbox AS sandbox
        FROM shop_orders WHERE id=$1
        """,
        order_id,
    )
    if not row:
        raise CommerceError("order not found")
    return {**dict(row), "currency": row["currency"].strip()}


async def attach_payment_preference(
    pool: Pool,
    order_id: UUID,
    *,
    checkout_url: str,
    provider_status_token: str,
    expires_at: datetime,
    sandbox: bool,
) -> None:
    await pool.execute(
        """
        UPDATE shop_orders SET payment_checkout_url=$2,payment_provider_status_token=$3,
            payment_expires_at=$4,payment_sandbox=$5,
            payment_status='pending',updated_at=now() WHERE id=$1
        """,
        order_id,
        checkout_url,
        provider_status_token,
        expires_at,
        sandbox,
    )


async def apply_payment_callback(
    pool: Pool,
    *,
    provider_event_id: str,
    external_reference: str,
    provider_intent_id: UUID,
    status: str,
    amount: int,
    currency: str,
    payload_hash: bytes,
) -> dict:
    prefix = "ecommerce:order:"
    if not external_reference.startswith(prefix):
        raise CommerceError("payment reference mismatch")
    try:
        order_id = UUID(external_reference.removeprefix(prefix))
    except ValueError as error:
        raise CommerceError("payment reference mismatch") from error
    async with transaction(pool) as connection:
        inserted = await connection.fetchval(
            """
            INSERT INTO payment_callback_events (provider_event_id,order_id,payload_hash,status)
            VALUES ($1,$2,$3,'received') ON CONFLICT (provider_event_id) DO NOTHING RETURNING id
            """,
            provider_event_id,
            order_id,
            payload_hash,
        )
        if inserted is None:
            return await _load_order(connection, order_id)
        order = await connection.fetchrow("SELECT * FROM shop_orders WHERE id=$1 FOR UPDATE", order_id)
        if not order or order["total"] != amount or order["currency"].strip() != currency:
            await connection.execute(
                "UPDATE payment_callback_events SET status='failed',error_code='mismatch',processed_at=now() WHERE id=$1",
                inserted,
            )
            raise CommerceError("payment amount mismatch")
        mapped = "rejected" if status in {"rejected", "cancelled"} else status
        order_status = order["status"]
        if status == "approved" and order_status == "pending":
            order_status = "confirmed"
        elif status == "expired" and order_status == "pending":
            order_status = "cancelled"
        await connection.execute(
            """
            UPDATE shop_orders SET payment_provider_intent_id=$2,payment_status=$3,
                status=$4,updated_at=now(),
                cancelled_at=CASE WHEN $4='cancelled' THEN now() ELSE cancelled_at END
            WHERE id=$1
            """,
            order_id,
            provider_intent_id,
            mapped,
            order_status,
        )
        if order_status == "cancelled" and order["status"] == "pending":
            items = await connection.fetch(
                "SELECT product_id,quantity FROM shop_order_items WHERE order_id=$1", order_id
            )
            for item in items:
                await connection.execute(
                    "UPDATE products SET qty=qty+$2,updated_at=now() WHERE id=$1",
                    item["product_id"],
                    item["quantity"],
                )
                await connection.execute(
                    "INSERT INTO stock_movements (product_id,delta,reason,created_by) VALUES ($1,$2,'payment expired','payments')",
                    item["product_id"],
                    item["quantity"],
                )
        await connection.execute(
            "UPDATE payment_callback_events SET status='processed',processed_at=now() WHERE id=$1",
            inserted,
        )
        return await _load_order(connection, order_id)


async def list_orders(pool: Pool, status: str | None, limit: int, offset: int) -> list[dict]:
    values: list[Any] = []
    where = ""
    if status:
        values.append(status)
        where = "WHERE o.status=$1"
    values.extend([limit, offset])
    rows = await pool.fetch(
        f"""
        SELECT o.id,o.order_number,o.customer_name,o.status,o.payment_method,
               o.payment_status,o.total,o.currency,count(i.id)::int AS item_count,o.created_at
        FROM shop_orders o LEFT JOIN shop_order_items i ON i.order_id=o.id
        {where}
        GROUP BY o.id ORDER BY o.created_at DESC
        LIMIT ${len(values)-1} OFFSET ${len(values)}
        """,
        *values,
    )
    return [{**dict(row), "currency": row["currency"].strip()} for row in rows]


async def admin_order(pool: Pool, order_id: UUID) -> dict:
    async with pool.acquire() as connection:
        return await _load_order(connection, order_id)


async def transition_order(
    pool: Pool, order_id: UUID, target: str, note: str, actor: str
) -> dict:
    transitions = {
        "pending": {"confirmed", "cancelled"},
        "confirmed": {"ready", "cancelled"},
        "ready": {"completed", "cancelled"},
        "completed": set(),
        "cancelled": set(),
    }
    async with transaction(pool) as connection:
        order = await connection.fetchrow("SELECT * FROM shop_orders WHERE id=$1 FOR UPDATE", order_id)
        if not order:
            raise CommerceError("order not found")
        if target not in transitions[order["status"]]:
            raise InvalidOrderTransition(f"invalid transition: {order['status']} -> {target}")
        if target == "cancelled":
            items = await connection.fetch(
                "SELECT product_id,quantity FROM shop_order_items WHERE order_id=$1", order_id
            )
            for item in items:
                await connection.execute(
                    "UPDATE products SET qty=qty+$2,updated_at=now() WHERE id=$1",
                    item["product_id"],
                    item["quantity"],
                )
                await connection.execute(
                    "INSERT INTO stock_movements (product_id,delta,reason,created_by) VALUES ($1,$2,$3,$4)",
                    item["product_id"],
                    item["quantity"],
                    f"cancelled order: {note}",
                    actor,
                )
        await connection.execute(
            """
            UPDATE shop_orders SET status=$2,updated_at=now(),
                completed_at=CASE WHEN $2='completed' THEN now() ELSE completed_at END,
                cancelled_at=CASE WHEN $2='cancelled' THEN now() ELSE cancelled_at END,
                cancellation_reason=CASE WHEN $2='cancelled' THEN $3 ELSE cancellation_reason END
            WHERE id=$1
            """,
            order_id,
            target,
            note,
        )
        await connection.execute(
            "INSERT INTO shop_order_status_history (order_id,from_status,to_status,note,actor) VALUES ($1,$2,$3,$4,$5)",
            order_id,
            order["status"],
            target,
            note,
            actor,
        )
        return await _load_order(connection, order_id)


async def admin_products(pool: Pool) -> list[dict]:
    rows = await pool.fetch(
        """
        SELECT p.id,p.name,p.sku,p.slug,p.qty,p.min_qty,p.price,p.active,p.description,
               p.short_description,p.image_url,p.gallery,p.featured,p.sort_order,c.slug AS category_slug
        FROM products p LEFT JOIN product_categories c ON c.id=p.category_id
        ORDER BY p.name
        """
    )
    return [_product(row) | {key: row[key] for key in ("qty", "min_qty", "active", "sort_order")} for row in rows]


async def admin_categories(pool: Pool) -> list[dict]:
    rows = await pool.fetch(
        """
        SELECT c.id, c.slug, c.name, c.description, c.sort_order, c.active,
               count(p.id)::int AS product_count
        FROM product_categories c
        LEFT JOIN products p ON p.category_id = c.id
        GROUP BY c.id
        ORDER BY c.sort_order, c.name
        """
    )
    return [dict(row) for row in rows]


async def create_category(pool: Pool, payload: dict) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO product_categories (slug, name, description, sort_order)
        VALUES ($1,$2,$3,$4)
        RETURNING id, slug, name, description, sort_order, active
        """ ,
        payload["slug"], payload["name"].strip(), payload.get("description", "").strip(),
        payload.get("sort_order", 0),
    )
    return dict(row)


async def patch_category(pool: Pool, category_id: UUID, payload: dict) -> dict:
    fields = {key: value for key, value in payload.items() if value is not None}
    if not fields:
        row = await pool.fetchrow("SELECT id,slug,name,description,sort_order,active FROM product_categories WHERE id=$1", category_id)
    else:
        assignments = []
        values: list[Any] = [category_id]
        for key, value in fields.items():
            values.append(value.strip() if isinstance(value, str) else value)
            assignments.append(f"{key}=${len(values)}")
        row = await pool.fetchrow(
            f"UPDATE product_categories SET {', '.join(assignments)},updated_at=now() WHERE id=$1 RETURNING id,slug,name,description,sort_order,active",
            *values,
        )
    if not row:
        raise CommerceError("category not found")
    return dict(row)


async def create_product(pool: Pool, payload: dict) -> dict:
    category_id = await _category_id(pool, payload.get("category_slug"))
    row = await pool.fetchrow(
        """
        INSERT INTO products (category_id, name, sku, slug, price, qty, min_qty)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        RETURNING id
        """,
        category_id, payload["name"].strip(), payload["sku"].strip(), payload["slug"],
        payload["price"], payload["qty"], payload.get("min_qty", 0),
    )
    return await _admin_product(pool, row["id"])


async def patch_product(pool: Pool, product_id: UUID, payload: dict) -> dict:
    fields = {key: value for key, value in payload.items() if value is not None}
    if "category_slug" in fields:
        fields["category_id"] = await _category_id(pool, fields.pop("category_slug"))
    if "gallery" in fields:
        fields["gallery"] = json.dumps(fields["gallery"])
    if not fields:
        return await _admin_product(pool, product_id)
    assignments = []
    values: list[Any] = [product_id]
    for key, value in fields.items():
        values.append(value.strip() if isinstance(value, str) else value)
        assignments.append(f"{key}=${len(values)}::jsonb" if key == "gallery" else f"{key}=${len(values)}")
    row = await pool.fetchrow(
        f"UPDATE products SET {', '.join(assignments)},updated_at=now() WHERE id=$1 RETURNING id",
        *values,
    )
    if not row:
        raise CommerceError("product not found")
    return await _admin_product(pool, product_id)


async def _category_id(pool: Pool, slug: str | None) -> UUID | None:
    if not slug:
        return None
    value = await pool.fetchval("SELECT id FROM product_categories WHERE slug=$1 AND active", slug)
    if not value:
        raise CommerceError("category not found")
    return value


async def _admin_product(pool: Pool, product_id: UUID) -> dict:
    row = await pool.fetchrow(
        """
        SELECT p.id,p.name,p.sku,p.slug,p.qty,p.min_qty,p.price,p.active,p.description,
               p.short_description,p.image_url,p.gallery,p.featured,p.sort_order,c.slug AS category_slug
        FROM products p LEFT JOIN product_categories c ON c.id=p.category_id WHERE p.id=$1
        """,
        product_id,
    )
    if not row:
        raise CommerceError("product not found")
    return _product(row)


async def adjust_stock(pool: Pool, product_id: UUID, delta: int, reason: str, actor: str) -> dict:
    async with transaction(pool) as connection:
        row = await connection.fetchrow(
            "UPDATE products SET qty=qty+$2,updated_at=now() WHERE id=$1 AND qty+$2>=0 RETURNING *",
            product_id,
            delta,
        )
        if not row:
            raise StockConflict("product not found or insufficient stock")
        if delta:
            await connection.execute(
                "INSERT INTO stock_movements (product_id,delta,reason,created_by) VALUES ($1,$2,$3,$4)",
                product_id,
                delta,
                reason,
                actor,
            )
        return dict(row)
