import asyncio
from app.tasks import celery_app


@celery_app.task(queue="notifications")
def notify_order_delivered(order_id: str, customer_id: str):
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.models.notification import Notification, NotificationType

        async with AsyncSessionLocal() as db:
            notif = Notification(
                user_id=customer_id,
                type=NotificationType.order_delivered,
                title="Order Delivered!",
                message=f"Your order #{order_id[:8].upper()} has been delivered.",
                data={"order_id": order_id},
            )
            db.add(notif)
            await db.commit()

    asyncio.run(_run())


@celery_app.task(queue="notifications")
def notify_vendor_approved(vendor_user_id: str):
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.models.notification import Notification, NotificationType

        async with AsyncSessionLocal() as db:
            notif = Notification(
                user_id=vendor_user_id,
                type=NotificationType.vendor_approved,
                title="Store Approved!",
                message="Your vendor application has been approved. Start listing products!",
                data={},
            )
            db.add(notif)
            await db.commit()

    asyncio.run(_run())
