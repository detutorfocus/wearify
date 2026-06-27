from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.vendor import Vendor
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.wallet import Wallet
from app.schemas.vendor import VendorRegister
from app.utils.helpers import generate_slug


class VendorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: VendorRegister, user_id: UUID) -> Vendor:
        # Check store name unique
        existing = await self.db.execute(
            select(Vendor).where(Vendor.store_name == data.store_name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Store name already taken")

        slug = await self._unique_slug(data.store_name)
        vendor = Vendor(
            user_id=user_id,
            store_name=data.store_name,
            store_slug=slug,
            description=data.description,
        )
        self.db.add(vendor)
        await self.db.flush()

        # Create wallet automatically
        wallet = Wallet(vendor_id=vendor.id)
        self.db.add(wallet)
        await self.db.flush()

        # Update user role to vendor
        from app.models.user import User, UserRole
        await self.db.execute(
            select(User).where(User.id == user_id)
        )
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.role = UserRole.vendor

        return vendor

    async def get_by_slug(self, slug: str) -> dict | None:
        result = await self.db.execute(
            select(Vendor)
            .options(selectinload(Vendor.products))
            .where(Vendor.store_slug == slug)
        )
        vendor = result.scalar_one_or_none()
        return self._serialize(vendor) if vendor else None

    async def get_dashboard_stats(self, user_id: UUID) -> dict:
        vendor = await self._get_vendor_by_user(user_id)

        # Total revenue
        revenue_result = await self.db.execute(
            select(func.sum(OrderItem.vendor_earnings))
            .join(Order)
            .where(
                OrderItem.vendor_id == vendor.id,
                Order.payment_status == "paid",
            )
        )
        total_revenue = float(revenue_result.scalar() or 0)

        # Total orders
        orders_result = await self.db.execute(
            select(func.count(OrderItem.id))
            .where(OrderItem.vendor_id == vendor.id)
        )
        total_orders = orders_result.scalar() or 0

        # Pending orders
        pending_result = await self.db.execute(
            select(func.count(OrderItem.id))
            .join(Order)
            .where(
                OrderItem.vendor_id == vendor.id,
                Order.status == OrderStatus.pending,
            )
        )
        pending_orders = pending_result.scalar() or 0

        # Total active products
        products_result = await self.db.execute(
            select(func.count(Product.id))
            .where(Product.vendor_id == vendor.id, Product.status == "active")
        )
        total_products = products_result.scalar() or 0

        wallet_result = await self.db.execute(
            select(Wallet).where(Wallet.vendor_id == vendor.id)
        )
        wallet = wallet_result.scalar_one_or_none()

        return {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "total_products": total_products,
            "pending_orders": pending_orders,
            "wallet_balance": float(wallet.balance) if wallet else 0,
            "pending_balance": float(wallet.pending_balance) if wallet else 0,
            "this_month_revenue": 0,  # implement with date filter
            "revenue_change_pct": 0,
        }

    async def _get_vendor_by_user(self, user_id: UUID) -> Vendor:
        result = await self.db.execute(
            select(Vendor).where(Vendor.user_id == user_id)
        )
        vendor = result.scalar_one_or_none()
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor profile not found")
        return vendor

    async def _unique_slug(self, name: str) -> str:
        base = generate_slug(name)
        slug = base
        counter = 1
        while True:
            exists = await self.db.execute(select(Vendor).where(Vendor.store_slug == slug))
            if not exists.scalar_one_or_none():
                return slug
            slug = f"{base}-{counter}"
            counter += 1

    def _serialize(self, vendor: Vendor) -> dict:
        return {
            "id": str(vendor.id),
            "store_name": vendor.store_name,
            "store_slug": vendor.store_slug,
            "description": vendor.description,
            "logo_url": vendor.logo_url,
            "banner_url": vendor.banner_url,
            "kyc_status": vendor.kyc_status,
            "subscription_plan": vendor.subscription_plan,
            "is_featured": vendor.is_featured,
            "rating": float(vendor.rating),
            "total_sales": vendor.total_sales,
            "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
        }
