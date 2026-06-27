# app/api/v1/endpoints/notifications.py
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, decode_token
from app.services.notification_service import NotificationService, ws_manager

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def get_notifications(
    page: int = 1,
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await NotificationService(db).list_for_user(
        current_user.id, page=page, unread_only=unread_only
    )


@router.post("/mark-read/{notification_id}")
async def mark_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    import uuid
    await NotificationService(db).mark_read(uuid.UUID(notification_id), current_user.id)
    await db.commit()
    return {"message": "Marked as read"}


@router.post("/mark-all-read")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    count = await NotificationService(db).mark_all_read(current_user.id)
    await db.commit()
    return {"message": f"{count} notifications marked as read"}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return
    user_id = payload.get("sub")
    await ws_manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()   # keep-alive ping
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id)
