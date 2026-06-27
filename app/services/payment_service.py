# app/services/payment_service.py
import hashlib
import hmac
import uuid
import stripe
import httpx

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.config import settings
from app.models.payment import Payment, PaymentProvider, PaymentStatus
from app.models.order import Order, OrderStatus
from app.models.wallet import Wallet, Transaction, TransactionType
from app.tasks.order_tasks import process_order_payment_success


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Initialize Payment ────────────────────────────────────────────────────

    async def initialize(
        self,
        order_id: uuid.UUID,
        provider: str,
        customer_email: str,
        amount: float,
        currency: str = "NGN",
    ) -> dict:
        reference = f"WEA-{uuid.uuid4().hex[:12].upper()}"

        if provider == "paystack":
            result = await self._paystack_init(amount, customer_email, reference, str(order_id))
        elif provider == "flutterwave":
            result = await self._flutterwave_init(amount, customer_email, reference, str(order_id), currency)
        elif provider == "stripe":
            result = await self._stripe_init(amount, customer_email, reference, str(order_id), currency)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported payment provider: {provider}")

        # Record pending payment
        payment = Payment(
            order_id=order_id,
            provider=PaymentProvider(provider),
            provider_reference=reference,
            amount=amount,
            currency=currency,
            status=PaymentStatus.pending,
        )
        self.db.add(payment)
        await self.db.commit()

        return result

    # ── Paystack ──────────────────────────────────────────────────────────────

    async def _paystack_init(self, amount: float, email: str, reference: str, order_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.paystack.co/transaction/initialize",
                headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET}"},
                json={
                    "amount": int(amount * 100),   # convert to kobo
                    "email": email,
                    "reference": reference,
                    "metadata": {"order_id": order_id},
                    "callback_url": f"{settings.FRONTEND_URL}/checkout/verify?provider=paystack",
                },
                timeout=30,
            )
        data = resp.json()
        if not data.get("status"):
            raise HTTPException(status_code=502, detail="Paystack initialization failed")
        return {"payment_url": data["data"]["authorization_url"], "reference": reference}

    def verify_paystack_webhook(self, payload: bytes, signature: str) -> bool:
        computed = hmac.new(
            settings.PAYSTACK_SECRET.encode("utf-8"),
            payload,
            hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(computed, signature)

    async def verify_paystack_transaction(self, reference: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.paystack.co/transaction/verify/{reference}",
                headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET}"},
                timeout=30,
            )
        return resp.json()

    # ── Flutterwave ───────────────────────────────────────────────────────────

    async def _flutterwave_init(
        self, amount: float, email: str, reference: str, order_id: str, currency: str
    ) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.flutterwave.com/v3/payments",
                headers={"Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET}"},
                json={
                    "tx_ref": reference,
                    "amount": amount,
                    "currency": currency,
                    "redirect_url": f"{settings.FRONTEND_URL}/checkout/verify?provider=flutterwave",
                    "customer": {"email": email},
                    "meta": {"order_id": order_id},
                },
                timeout=30,
            )
        data = resp.json()
        if data.get("status") != "success":
            raise HTTPException(status_code=502, detail="Flutterwave initialization failed")
        return {"payment_url": data["data"]["link"], "reference": reference}

    def verify_flutterwave_webhook(self, payload: bytes, signature: str) -> bool:
        computed = hmac.new(
            settings.FLUTTERWAVE_SECRET.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, signature)

    # ── Stripe ────────────────────────────────────────────────────────────────

    async def _stripe_init(
        self, amount: float, email: str, reference: str, order_id: str, currency: str
    ) -> dict:
        stripe.api_key = settings.STRIPE_SECRET
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": currency.lower(),
                    "product_data": {"name": "Wearify Order"},
                    "unit_amount": int(amount * 100),
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{settings.FRONTEND_URL}/checkout/verify?provider=stripe&ref={reference}",
            cancel_url=f"{settings.FRONTEND_URL}/checkout/cancelled",
            client_reference_id=order_id,
            metadata={"reference": reference},
        )
        return {"payment_url": session.url, "reference": reference}

    # ── Process Successful Payment ────────────────────────────────────────────

    async def handle_successful_payment(self, reference: str, provider: str) -> None:
        """
        Called after webhook confirms payment success.
        IDEMPOTENT — safe to call multiple times for same reference.
        """
        # Fetch payment record
        result = await self.db.execute(
            select(Payment).where(Payment.provider_reference == reference)
        )
        payment = result.scalar_one_or_none()

        if not payment:
            return  # Unknown reference, ignore

        if payment.status == PaymentStatus.success:
            return  # Already processed — idempotency guard

        # Update payment status
        payment.status = PaymentStatus.success
        await self.db.flush()

        # Update order status
        await self.db.execute(
            update(Order)
            .where(Order.id == payment.order_id)
            .values(status=OrderStatus.confirmed, payment_status="paid")
        )

        await self.db.commit()

        # Dispatch background task to credit vendor wallets
        # (done async to not block webhook response)
        process_order_payment_success.delay(str(payment.order_id))

    # ── Credit Vendor Wallets (called by Celery) ──────────────────────────────

    async def credit_vendor_wallets(self, order_id: uuid.UUID) -> None:
        """
        Distribute vendor earnings after order payment.
        Called from Celery task after brief delay to ensure DB consistency.
        """
        from app.models.order import OrderItem
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return

        for item in order.items:
            # Get or create wallet
            wallet_result = await self.db.execute(
                select(Wallet).where(Wallet.vendor_id == item.vendor_id)
            )
            wallet = wallet_result.scalar_one_or_none()
            if not wallet:
                continue

            earnings = item.vendor_earnings

            # Update wallet balance
            wallet.pending_balance += earnings  # moves to balance after delivery confirmation
            wallet.total_earned += earnings

            # Record transaction
            txn = Transaction(
                wallet_id=wallet.id,
                type=TransactionType.credit,
                amount=earnings,
                balance_after=wallet.balance + wallet.pending_balance,
                reference=f"ORDER-{order_id}",
                description=f"Earnings from order #{str(order_id)[:8]}",
                status="pending",
            )
            self.db.add(txn)

        await self.db.commit()
