"""
Analytics service — vendor dashboard analytics and admin platform analytics.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User
from app.models.vendor import Vendor
from app.models.payment import Payment, PaymentStatus


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Vendor Analytics ──────────────────────────────────────────────────────

    async def vendor_analytics(self, vendor_id: UUID, range_days: int = 30) -> dict:
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=range_days)
        prev_since = since - timedelta(days=range_days)

        # Current period revenue
        rev = await self._vendor_revenue(vendor_id, since, now)
        prev_rev = await self._vendor_revenue(vendor_id, prev_since, since)

        # Orders count
        orders = await self._vendor_order_count(vendor_id, since, now)
        prev_orders = await self._vendor_order_count(vendor_id, prev_since, since)

        # Top products
        top_products = await self._vendor_top_products(vendor_id, since, now)

        # Daily revenue breakdown
        daily = await self._vendor_daily_revenue(vendor_id, since, now)

        return {
            "period_days": range_days,
            "total_revenue": rev,
            "total_orders": orders,
            "avg_order_value": rev / orders if orders > 0 else 0,
            "total_units_sold": sum(p["units_sold"] for p in top_products),
            "revenue_change_pct": self._pct_change(prev_rev, rev),
            "orders_change_pct": self._pct_change(prev_orders, orders),
            "daily_revenue": daily,
            "top_products": top_products,
            "top_categories": [],
        }

    async def _vendor_revenue(self, vendor_id: UUID, since: datetime, until: datetime) -> float:
        result = await self.db.execute(
            select(func.coalesce(func.sum(OrderItem.vendor_earnings), 0))
            .join(Order)
            .where(
                OrderItem.vendor_id == vendor_id,
                Order.payment_status == "paid",
                Order.created_at >= since,
                Order.created_at <= until,
            )
        )
        return float(result.scalar() or 0)

    async def _vendor_order_count(self, vendor_id: UUID, since: datetime, until: datetime) -> int:
        result = await self.db.execute(
            select(func.count(OrderItem.id))
            .join(Order)
            .where(
                OrderItem.vendor_id == vendor_id,
                Order.created_at >= since,
                Order.created_at <= until,
            )
        )
        return int(result.scalar() or 0)

    async def _vendor_top_products(self, vendor_id: UUID, since: datetime, until: datetime) -> list:
        result = await self.db.execute(
            select(
                OrderItem.product_id,
                func.sum(OrderItem.quantity).label("units_sold"),
                func.sum(OrderItem.vendor_earnings).label("revenue"),
            )
            .join(Order)
            .where(
                OrderItem.vendor_id == vendor_id,
                Order.payment_status == "paid",
                Order.created_at >= since,
                Order.created_at <= until,
            )
            .group_by(OrderItem.product_id)
            .order_by(func.sum(OrderItem.vendor_earnings).desc())
            .limit(5)
        )
        rows = result.all()
        products = []
        for row in rows:
            prod = await self.db.execute(
                select(Product).where(Product.id == row.product_id)
            )
            p = prod.scalar_one_or_none()
            if p:
                products.append({
                    "product_id": str(p.id),
                    "product_name": p.name,
                    "slug": p.slug,
                    "units_sold": int(row.units_sold or 0),
                    "revenue": float(row.revenue or 0),
                })
        return products

    async def _vendor_daily_revenue(self, vendor_id: UUID, since: datetime, until: datetime) -> list:
        result = await self.db.execute(
            select(
                func.date(Order.created_at).label("day"),
                func.sum(OrderItem.vendor_earnings).label("revenue"),
                func.count(OrderItem.id).label("orders"),
            )
            .join(Order)
            .where(
                OrderItem.vendor_id == vendor_id,
                Order.payment_status == "paid",
                Order.created_at >= since,
                Order.created_at <= until,
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )
        return [
            {
                "date": str(row.day),
                "revenue": float(row.revenue or 0),
                "orders": int(row.orders or 0),
            }
            for row in result.all()
        ]

    # ── Admin Analytics ───────────────────────────────────────────────────────

    async def platform_analytics(self, range_days: int = 30) -> dict:
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=range_days)
        prev_since = since - timedelta(days=range_days)

        # Revenue
        revenue = float((await self.db.execute(
            select(func.coalesce(func.sum(Order.total), 0))
            .where(Order.payment_status == "paid", Order.created_at >= since)
        )).scalar() or 0)

        prev_revenue = float((await self.db.execute(
            select(func.coalesce(func.sum(Order.total), 0))
            .where(Order.payment_status == "paid",
                   Order.created_at >= prev_since, Order.created_at < since)
        )).scalar() or 0)

        # Commission (platform earnings)
        commission = float((await self.db.execute(
            select(func.coalesce(func.sum(OrderItem.vendor_commission), 0))
            .join(Order)
            .where(Order.payment_status == "paid", Order.created_at >= since)
        )).scalar() or 0)

        # Orders
        orders = int((await self.db.execute(
            select(func.count(Order.id)).where(Order.created_at >= since)
        )).scalar() or 0)

        # New users & vendors
        new_users = int((await self.db.execute(
            select(func.count(User.id)).where(User.created_at >= since)
        )).scalar() or 0)

        new_vendors = int((await self.db.execute(
            select(func.count(Vendor.id)).where(Vendor.created_at >= since)
        )).scalar() or 0)

        # Order status breakdown
        status_rows = await self.db.execute(
            select(Order.status, func.count(Order.id))
            .where(Order.created_at >= since)
            .group_by(Order.status)
        )
        status_breakdown = {str(row[0]): row[1] for row in status_rows.all()}

        # Payment provider breakdown
        provider_rows = await self.db.execute(
            select(Payment.provider, func.count(Payment.id))
            .where(Payment.status == PaymentStatus.success, Payment.created_at >= since)
            .group_by(Payment.provider)
        )
        provider_breakdown = {str(row[0]): row[1] for row in provider_rows.all()}

        # Daily revenue
        daily = await self._platform_daily_revenue(since, now)

        # Top vendors
        top_vendors = await self._top_vendors(since, now)

        return {
            "period_days": range_days,
            "total_revenue": revenue,
            "total_orders": orders,
            "new_users": new_users,
            "new_vendors": new_vendors,
            "avg_order_value": revenue / orders if orders > 0 else 0,
            "gmv": revenue,
            "platform_commission": commission,
            "revenue_change_pct": self._pct_change(prev_revenue, revenue),
            "daily_revenue": daily,
            "top_vendors": top_vendors,
            "order_status_breakdown": status_breakdown,
            "payment_provider_breakdown": provider_breakdown,
        }

    async def _platform_daily_revenue(self, since: datetime, until: datetime) -> list:
        result = await self.db.execute(
            select(
                func.date(Order.created_at).label("day"),
                func.sum(Order.total).label("revenue"),
                func.count(Order.id).label("orders"),
            )
            .where(
                Order.payment_status == "paid",
                Order.created_at >= since,
                Order.created_at <= until,
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )
        return [
            {"date": str(r.day), "revenue": float(r.revenue or 0), "orders": int(r.orders or 0)}
            for r in result.all()
        ]

    async def _top_vendors(self, since: datetime, until: datetime) -> list:
        result = await self.db.execute(
            select(
                OrderItem.vendor_id,
                func.sum(OrderItem.vendor_earnings).label("revenue"),
                func.count(OrderItem.id).label("orders"),
            )
            .join(Order)
            .where(Order.payment_status == "paid",
                   Order.created_at >= since, Order.created_at <= until)
            .group_by(OrderItem.vendor_id)
            .order_by(func.sum(OrderItem.vendor_earnings).desc())
            .limit(10)
        )
        vendors = []
        for row in result.all():
            v = (await self.db.execute(
                select(Vendor).where(Vendor.id == row.vendor_id)
            )).scalar_one_or_none()
            if v:
                vendors.append({
                    "vendor_id": str(v.id),
                    "store_name": v.store_name,
                    "store_slug": v.store_slug,
                    "revenue": float(row.revenue or 0),
                    "orders": int(row.orders or 0),
                })
        return vendors

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _pct_change(old: float, new: float) -> float:
        if old == 0:
            return 100.0 if new > 0 else 0.0
        return round(((new - old) / old) * 100, 1)
