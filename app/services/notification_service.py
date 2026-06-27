"""
Notification service — create, list, mark-read.
Also contains the WebSocket connection manager for real-time delivery.
"""
import json
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import WebSocket

from app.models.notification import Notification, NotificationType


class ConnectionManager:
    """
    In-memory WebSocket registry.
    For multi-process deployments, replace with Redis pub/sub.
    """

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id] = websocket

    def disconnect(self, user_id: str) -> None:
        self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, payload: dict) -> None:
        ws = self._connections.get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                self.disconnect(user_id)

    async def broadcast_admin(self, payload: dict) -> None:
        """Broadcast to all connected admin users."""
        for ws in list(self._connections.values()):
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                pass

    @property
    def online_count(self) -> int:
        return len(self._connections)


# Singleton connection manager (per process)
ws_manager = ConnectionManager()


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: dict | None = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            data=data or {},
        )
        self.db.add(notif)
        await self.db.flush()

        # Attempt real-time delivery via WebSocket
        await ws_manager.send_to_user(str(user_id), {
            "type": "notification",
            "data": {
                "id": str(notif.id),
                "type": notification_type,
                "title": title,
                "message": message,
                "data": data or {},
                "is_read": False,
            }
        })
        return notif

    async def list_for_user(
        self, user_id: UUID, page: int = 1, page_size: int = 50, unread_only: bool = False
    ) -> dict:
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read == False)
        query = query.order_by(Notification.created_at.desc())

        result = await self.db.execute(query.offset((page - 1) * page_size).limit(page_size))
        notifications = result.scalars().all()

        return {
            "items": [
                {
                    "id": str(n.id),
                    "type": n.type,
                    "title": n.title,
                    "message": n.message,
                    "is_read": n.is_read,
                    "data": n.data,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notifications
            ],
            "unread_count": sum(1 for n in notifications if not n.is_read),
        }

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> None:
        await self.db.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
        )

    async def mark_all_read(self, user_id: UUID) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        return result.rowcount
