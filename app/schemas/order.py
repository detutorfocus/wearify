from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.models.order import OrderStatus


class ShippingAddress(BaseModel):
    full_name: str
    phone: str
    address_line1: str
    address_line2: str | None = None
    city: str
    state: str
    country: str = "Nigeria"
    postal_code: str | None = None


class OrderItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    vendor_id: UUID
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    shipping_address: ShippingAddress
    payment_method: str
    notes: str | None = None


class OrderResponse(BaseModel):
    id: UUID
    customer_id: UUID
    status: OrderStatus
    subtotal: Decimal
    shipping_fee: Decimal
    discount: Decimal
    total: Decimal
    shipping_address: dict
    payment_method: str | None
    payment_status: str
    tracking_number: str | None
    items: list[OrderItemResponse] = []
    created_at: datetime
    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    page: int
    page_size: int
