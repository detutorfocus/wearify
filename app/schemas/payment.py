"""
Pydantic schemas for payment endpoints.
"""
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.models.payment import PaymentProvider, PaymentStatus


class PaymentInitRequest(BaseModel):
    order_id: UUID
    provider: PaymentProvider
    currency: str = "NGN"


class PaymentInitResponse(BaseModel):
    payment_url: str
    reference: str
    provider: PaymentProvider


class PaymentResponse(BaseModel):
    id: UUID
    order_id: UUID
    provider: PaymentProvider
    provider_reference: str
    amount: float
    currency: str
    status: PaymentStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookPaystackPayload(BaseModel):
    event: str
    data: dict


class WebhookFlutterwavePayload(BaseModel):
    event: str
    data: dict


class PaymentVerifyResponse(BaseModel):
    status: str
    message: str
    order_id: str | None = None
