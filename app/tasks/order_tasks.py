import asyncio
from app.tasks import celery_app


@celery_app.task(queue="orders", max_retries=3, default_retry_delay=30)
def process_order_payment_success(order_id: str):
    """Credit vendor wallets after successful payment. Called by payment webhook."""
    import uuid

    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.services.payment_service import PaymentService

        async with AsyncSessionLocal() as db:
            service = PaymentService(db)
            await service.credit_vendor_wallets(uuid.UUID(order_id))

        # Fire confirmation email
        from app.core.database import AsyncSessionLocal
        from app.models.order import Order
        from app.models.user import User
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Order).options(selectinload(Order.customer)).where(Order.id == uuid.UUID(order_id))
            )
            order = result.scalar_one_or_none()
            if order and order.customer:
                from app.tasks.email_tasks import send_order_confirmation_email
                send_order_confirmation_email.delay(
                    order_id, order.customer.email, float(order.total)
                )

    asyncio.run(_run())


@celery_app.task(queue="orders")
def release_pending_wallet_balances():
    """Release pending wallet balances 7 days after order delivery."""
    async def _run():
        from datetime import datetime, timedelta, timezone
        from app.core.database import AsyncSessionLocal
        from app.models.wallet import Wallet, Transaction, TransactionType
        from app.models.order import Order, OrderStatus
        from app.models.order import OrderItem
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Order)
                .options(selectinload(Order.items))
                .where(Order.status == OrderStatus.delivered, Order.updated_at <= cutoff)
            )
            orders = result.scalars().all()

            for order in orders:
                for item in order.items:
                    wallet_result = await db.execute(
                        select(Wallet).where(Wallet.vendor_id == item.vendor_id)
                    )
                    wallet = wallet_result.scalar_one_or_none()
                    if wallet and wallet.pending_balance > 0:
                        amount = item.vendor_earnings
                        wallet.balance += amount
                        wallet.pending_balance = max(0, wallet.pending_balance - amount)

                        txn = Transaction(
                            wallet_id=wallet.id,
                            type=TransactionType.credit,
                            amount=amount,
                            balance_after=wallet.balance,
                            description=f"Released from order #{str(order.id)[:8]}",
                            status="completed",
                        )
                        db.add(txn)

            await db.commit()

    asyncio.run(_run())
