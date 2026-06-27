"""
Business-logic validators used across services.
"""
import re
from decimal import Decimal
from fastapi import HTTPException


def validate_price(price: Decimal, label: str = "Price") -> None:
    if price <= 0:
        raise HTTPException(status_code=422, detail=f"{label} must be greater than 0")


def validate_sale_price(base_price: Decimal, sale_price: Decimal | None) -> None:
    if sale_price is not None and sale_price >= base_price:
        raise HTTPException(
            status_code=422,
            detail="Sale price must be less than base price",
        )


def validate_phone(phone: str) -> str:
    """Normalise and validate Nigerian/international phone numbers."""
    cleaned = re.sub(r"[\s\-\(\)]", "", phone)
    if not re.match(r"^\+?[0-9]{7,15}$", cleaned):
        raise HTTPException(status_code=422, detail=f"Invalid phone number: {phone}")
    return cleaned


def validate_stock(requested: int, available: int, product_name: str) -> None:
    if requested > available:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock for '{product_name}'. "
                   f"Requested: {requested}, Available: {available}",
        )


def validate_withdrawal_amount(amount: Decimal, balance: Decimal, min_amount: float) -> None:
    if float(amount) < min_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum withdrawal amount is {min_amount:,.0f}",
        )
    if amount > balance:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")


def validate_image_content_type(content_type: str) -> None:
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if content_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {content_type}. Allowed: {', '.join(allowed)}",
        )


def validate_file_size(size_bytes: int, max_mb: int) -> None:
    max_bytes = max_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {max_mb}MB",
        )
