"""
Custom FastAPI middleware for Wearify.
Handles: audit logging, request timing, security headers.
"""
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Logs all mutating requests (POST, PUT, PATCH, DELETE) to the audit_logs table.
    Never raises — logging failures must not break the API.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Skip logging for these paths
        self.skip_paths = {
            "/health",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/api/v1/payments/webhooks/paystack",
            "/api/v1/payments/webhooks/flutterwave",
            "/api/v1/payments/webhooks/stripe",
        }
        self.log_methods = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 1)

        # Add timing header on all responses
        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        response.headers["X-Request-ID"] = str(uuid.uuid4())

        # Audit log write operations
        if (
            request.method in self.log_methods
            and request.url.path not in self.skip_paths
        ):
            try:
                await self._write_audit_log(request, response, duration_ms)
            except Exception:
                pass  # Never break the response

        return response

    async def _write_audit_log(self, request: Request, response: Response, duration_ms: float):
        from app.core.security import decode_token
        from app.core.database import AsyncSessionLocal
        from app.models.audit import AuditLog

        # Extract user from token if present
        user_id = None
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            payload = decode_token(auth[7:])
            if payload:
                user_id = payload.get("sub")

        # Extract resource from path: /api/v1/products/abc → products
        path_parts = request.url.path.strip("/").split("/")
        resource = path_parts[2] if len(path_parts) > 2 else request.url.path
        resource_id = path_parts[3] if len(path_parts) > 3 else None

        async with AsyncSessionLocal() as db:
            log = AuditLog(
                user_id=user_id,
                action=request.method,
                resource=resource,
                resource_id=resource_id,
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("user-agent", "")[:500],
                payload={
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "path": request.url.path,
                    "query": str(request.query_params) or None,
                },
            )
            db.add(log)
            await db.commit()

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Respect X-Forwarded-For header (set by Nginx)."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
