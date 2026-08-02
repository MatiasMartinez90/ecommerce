import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

PHONE_RE = re.compile(r"^\+?[0-9\s()\-]{7,24}$")


class CategoryOut(BaseModel):
    slug: str
    name: str
    description: str
    product_count: int


class ProductOut(BaseModel):
    id: UUID
    slug: str
    name: str
    sku: str
    description: str
    short_description: str
    category_slug: str | None
    category_name: str | None
    image_url: str | None
    video_url: str | None
    gallery: list[str]
    price: int
    available_qty: int
    in_stock: bool
    featured: bool


class ProductListOut(BaseModel):
    items: list[ProductOut]
    total: int
    limit: int
    offset: int


class CartCreateIn(BaseModel):
    customer_email: EmailStr | None = None


class CartItemSetIn(BaseModel):
    quantity: int = Field(ge=0, le=99)


class CartItemOut(BaseModel):
    product: ProductOut
    quantity: int
    line_total: int


class CartOut(BaseModel):
    token: str
    status: str
    currency: str
    items: list[CartItemOut]
    subtotal: int
    total_quantity: int
    expires_at: datetime


class AbandonedCartOut(BaseModel):
    id: UUID
    customer_email: EmailStr | None
    status: Literal["abandoned"]
    last_activity: datetime
    abandoned_at: datetime
    recovery_attempts: int
    total: int
    item_count: int


class CheckoutCustomerIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value: str) -> str:
        value = value.strip()
        if not PHONE_RE.match(value):
            raise ValueError("invalid phone")
        return re.sub(r"[\s\-()]", "", value)


class CheckoutIn(BaseModel):
    cart_token: str = Field(min_length=32, max_length=128)
    customer: CheckoutCustomerIn
    payment_method: Literal["pay_at_store", "mercado_pago"] = "pay_at_store"
    customer_notes: str = Field(default="", max_length=1000)


class OrderItemOut(BaseModel):
    product_slug: str
    product_name: str
    sku: str
    unit_price: int
    quantity: int
    line_total: int


class OrderOut(BaseModel):
    id: UUID
    order_number: int
    customer_name: str
    customer_email: str
    customer_phone: str
    status: str
    payment_method: str
    payment_status: str
    currency: str
    subtotal: int
    total: int
    pickup_location: str
    customer_notes: str
    cancellation_reason: str
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemOut]


class PaymentPreferenceIn(BaseModel):
    cart_token: str = Field(min_length=32, max_length=128)


class PaymentPreferenceOut(BaseModel):
    checkout_url: str
    status_token: str
    status: str
    amount: int
    currency: str
    expires_at: datetime
    sandbox: bool


class PaymentStatusOut(BaseModel):
    purpose: Literal["shop_order"] = "shop_order"
    status: str
    amount: int
    currency: str
    expires_at: datetime
    sandbox: bool


class PaymentCallbackIn(BaseModel):
    event: Literal[
        "payment.pending",
        "payment.approved",
        "payment.rejected",
        "payment.cancelled",
        "payment.refunded",
        "payment.expired",
    ]
    payment_intent_id: UUID
    tenant_id: str
    external_reference: str
    status: Literal["pending", "approved", "rejected", "cancelled", "refunded", "expired"]
    amount: int = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    occurred_at: datetime


class OrderStatusIn(BaseModel):
    status: Literal["confirmed", "ready", "completed", "cancelled"]
    note: str = Field(default="", max_length=500)


class ProductCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    sku: str = Field(min_length=2, max_length=100)
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    price: int = Field(gt=0, le=1_000_000_000)
    qty: int = Field(ge=0, le=1_000_000)
    min_qty: int = Field(default=0, ge=0, le=1_000_000)
    category_slug: str | None = None
    video_url: HttpUrl | None = None


class CategoryCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    description: str = Field(default="", max_length=1000)
    sort_order: int = Field(default=0, ge=0, le=10000)


class CategoryPatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    sort_order: int | None = Field(default=None, ge=0, le=10000)
    active: bool | None = None


class ProductPatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    price: int | None = Field(default=None, gt=0, le=1_000_000_000)
    min_qty: int | None = Field(default=None, ge=0, le=1_000_000)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=5000)
    short_description: str | None = Field(default=None, max_length=500)
    category_slug: str | None = None
    image_url: HttpUrl | None = None
    video_url: HttpUrl | None = None
    gallery: list[HttpUrl] | None = Field(default=None, max_length=12)
    featured: bool | None = None
    sort_order: int | None = None
    active: bool | None = None


class StockAdjustIn(BaseModel):
    delta: int = Field(ge=-1_000_000, le=1_000_000)
    reason: str = Field(default="manual adjustment", max_length=300)
