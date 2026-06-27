from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.models.vendor import KYCStatus, SubscriptionPlan


class VendorRegister(BaseModel):
    store_name: str
    description: str | None = None


class VendorProfileUpdate(BaseModel):
    store_name: str | None = None
    description: str | None = None
    logo_url: str | None = None
    banner_url: str | None = None


class VendorResponse(BaseModel):
    id: UUID
    store_name: str
    store_slug: str
    description: str | None
    logo_url: str | None
    banner_url: str | None
    kyc_status: KYCStatus
    subscription_plan: SubscriptionPlan
    is_featured: bool
    rating: Decimal
    total_sales: int
    created_at: datetime
    model_config = {"from_attributes": True}


class VendorDashboardStats(BaseModel):
    total_revenue: float
    total_orders: int
    total_products: int
    pending_orders: int
    wallet_balance: float
    pending_balance: float
    this_month_revenue: float
    revenue_change_pct: float


class WithdrawalRequest(BaseModel):
    amount: Decimal
    bank_code: str
    account_number: str
    account_name: str
