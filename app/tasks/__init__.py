from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "wearify",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.order_tasks",
        "app.tasks.notification_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.tasks.email_tasks.*": {"queue": "emails"},
        "app.tasks.order_tasks.*": {"queue": "orders"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
    },
    beat_schedule={
        "release-pending-wallets": {
            "task": "app.tasks.order_tasks.release_pending_wallet_balances",
            "schedule": 3600,
        },
    },
)
