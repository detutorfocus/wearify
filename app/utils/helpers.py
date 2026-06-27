import re
import uuid
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from app.core.config import settings


def generate_slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def generate_sku(vendor_slug: str, product_name: str) -> str:
    prefix = vendor_slug[:3].upper()
    name_part = re.sub(r"[^A-Z0-9]", "", product_name.upper())[:4]
    unique = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{name_part}-{unique}"


def generate_email_token(user_id: str) -> str:
    payload = f"{user_id}:{datetime.now(timezone.utc).timestamp()}"
    return hmac.new(
        settings.JWT_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def generate_reset_token(user_id: str) -> str:
    expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
    payload = f"{user_id}:{expiry}"
    sig = hmac.new(settings.JWT_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def verify_reset_token(token: str) -> str | None:
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None
        user_id, expiry, sig = parts
        expiry_dt = datetime.fromtimestamp(float(expiry), tz=timezone.utc)
        if expiry_dt < datetime.now(timezone.utc):
            return None
        expected_sig = hmac.new(
            settings.JWT_SECRET.encode(),
            f"{user_id}:{expiry}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        return user_id
    except Exception:
        return None
