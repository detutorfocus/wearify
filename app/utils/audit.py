from fastapi import Request, Response
from app.models.audit import AuditLog
from app.core.security import decode_token


async def log_request(request: Request, response: Response) -> None:
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user_id = None
        if token:
            payload = decode_token(token)
            if payload:
                user_id = payload.get("sub")

        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            log = AuditLog(
                user_id=user_id,
                action=request.method,
                resource=request.url.path,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            db.add(log)
            await db.commit()
    except Exception:
        pass  # never let audit logging break the app
