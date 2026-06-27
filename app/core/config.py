# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # ── App ──────────────────────────────────────────────
    APP_ENV: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Wearify API"
    VERSION: str = "1.0.0"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Database ─────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://wearify:secret@localhost:5432/wearify"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40

    # ── Redis ────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ──────────────────────────────────────────────
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Payments ─────────────────────────────────────────
    PAYSTACK_SECRET: str = ""
    PAYSTACK_PUBLIC: str = ""
    FLUTTERWAVE_SECRET: str = ""
    FLUTTERWAVE_PUBLIC: str = ""
    STRIPE_SECRET: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # ── Storage ──────────────────────────────────────────
    STORAGE_BACKEND: str = "cloudinary"  # "cloudinary" or "s3"
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = ""
    AWS_REGION: str = "us-east-1"

    # ── Email ────────────────────────────────────────────
    SENDGRID_API_KEY: str = ""
    MAIL_FROM: str = "noreply@wearify.com"
    MAIL_FROM_NAME: str = "Wearify"

    # ── SMS ──────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # ── Google OAuth ─────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # ── Platform Config ──────────────────────────────────
    DEFAULT_COMMISSION_RATE: float = 10.0  # 10% platform commission
    MIN_WITHDRAWAL_AMOUNT: float = 1000.0  # min ₦1000 or $10
    MAX_UPLOAD_SIZE_MB: int = 10
    MAX_PRODUCT_IMAGES: int = 8

    # ── Sentry ───────────────────────────────────────────
    SENTRY_DSN: str = ""


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
