from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


class PaymentInitRequest(BaseModel):
    order_id: str
    provider: str  # paystack | flutterwave | stripe
    currency: str = "NGN"


@router.post("/initialize")
async def initialize_payment(
    data: PaymentInitRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.models.order import Order
    from sqlalchemy import select
    import uuid

    # Verify order belongs to current user
    result = await db.execute(select(Order).where(Order.id == uuid.UUID(data.order_id)))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if str(order.customer_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    service = PaymentService(db)
    return await service.initialize(
        order_id=order.id,
        provider=data.provider,
        customer_email=current_user.email,
        amount=float(order.total),
        currency=data.currency,
    )


@router.post("/verify/{reference}")
async def verify_payment(
    reference: str,
    provider: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = PaymentService(db)

    if provider == "paystack":
        result = await service.verify_paystack_transaction(reference)
        if result.get("data", {}).get("status") == "success":
            await service.handle_successful_payment(reference, provider)
            return {"status": "success", "message": "Payment verified"}
    elif provider == "flutterwave":
        # Flutterwave verify via transaction ID
        pass

    raise HTTPException(status_code=400, detail="Payment verification failed")


@router.post("/webhooks/paystack")
async def paystack_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    service = PaymentService(db)
    if not service.verify_paystack_webhook(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    import json
    event = json.loads(payload)

    if event.get("event") == "charge.success":
        reference = event["data"]["reference"]
        await service.handle_successful_payment(reference, "paystack")

    # Store raw webhook
    from app.models.payment import Payment
    from sqlalchemy import select
    result = await db.execute(
        select(Payment).where(Payment.provider_reference == event.get("data", {}).get("reference"))
    )
    payment = result.scalar_one_or_none()
    if payment:
        payment.webhook_payload = event
        await db.commit()

    return {"status": "ok"}


@router.post("/webhooks/flutterwave")
async def flutterwave_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    signature = request.headers.get("verif-hash", "")

    import json
    from app.core.config import settings
    if signature != settings.FLUTTERWAVE_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = json.loads(payload)
    if event.get("event") == "charge.completed" and event.get("data", {}).get("status") == "successful":
        reference = event["data"]["tx_ref"]
        service = PaymentService(db)
        await service.handle_successful_payment(reference, "flutterwave")

    return {"status": "ok"}


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    import stripe
    from app.core.config import settings

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid stripe signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        reference = session.get("metadata", {}).get("reference")
        if reference:
            service = PaymentService(db)
            await service.handle_successful_payment(reference, "stripe")

    return {"status": "ok"}
