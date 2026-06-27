from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import require_admin
from app.models.vendor import Vendor, KYCStatus
from app.models.product import Product, ProductStatus
from app.models.order import Order
from app.models.user import User
from app.models.payment import Payment

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    total_vendors = (await db.execute(select(func.count(Vendor.id)))).scalar()
    pending_vendors = (await db.execute(
        select(func.count(Vendor.id)).where(Vendor.kyc_status == KYCStatus.pending)
    )).scalar()
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar()
    total_revenue = (await db.execute(
        select(func.sum(Order.total)).where(Order.payment_status == "paid")
    )).scalar() or 0
    total_products = (await db.execute(
        select(func.count(Product.id)).where(Product.status == ProductStatus.active)
    )).scalar()

    return {
        "total_users": total_users,
        "total_vendors": total_vendors,
        "pending_vendors": pending_vendors,
        "total_orders": total_orders,
        "total_revenue": float(total_revenue),
        "total_products": total_products,
    }


@router.get("/vendors")
async def list_vendors(
    page: int = 1,
    page_size: int = 20,
    kyc_status: str = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    query = select(Vendor)
    if kyc_status:
        query = query.where(Vendor.kyc_status == kyc_status)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    offset = (page - 1) * page_size
    result = await db.execute(query.order_by(Vendor.created_at.desc()).offset(offset).limit(page_size))
    vendors = result.scalars().all()

    return {
        "items": [
            {
                "id": str(v.id),
                "store_name": v.store_name,
                "store_slug": v.store_slug,
                "kyc_status": v.kyc_status,
                "subscription_plan": v.subscription_plan,
                "is_featured": v.is_featured,
                "total_sales": v.total_sales,
                "created_at": v.created_at.isoformat(),
            }
            for v in vendors
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


class VendorAction(BaseModel):
    reason: str | None = None


@router.put("/vendors/{vendor_id}/approve")
async def approve_vendor(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    vendor.kyc_status = KYCStatus.approved

    # Notify vendor
    try:
        from app.tasks.notification_tasks import notify_vendor_approved
        notify_vendor_approved.delay(str(vendor.user_id))
    except Exception:
        pass

    await db.commit()
    return {"message": "Vendor approved"}


@router.put("/vendors/{vendor_id}/reject")
async def reject_vendor(
    vendor_id: str,
    data: VendorAction,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    vendor.kyc_status = KYCStatus.rejected
    await db.commit()
    return {"message": "Vendor rejected"}


@router.get("/products")
async def list_all_products(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    query = select(Product)
    if status:
        query = query.where(Product.status == status)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    offset = (page - 1) * page_size
    result = await db.execute(query.order_by(Product.created_at.desc()).offset(offset).limit(page_size))
    products = result.scalars().all()

    return {
        "items": [
            {
                "id": str(p.id),
                "name": p.name,
                "slug": p.slug,
                "base_price": float(p.base_price),
                "status": p.status,
                "stock_quantity": p.stock_quantity,
                "vendor_id": str(p.vendor_id),
                "created_at": p.created_at.isoformat(),
            }
            for p in products
        ],
        "total": total,
    }


class ModerateAction(BaseModel):
    action: str  # "approve" | "reject" | "archive"


@router.put("/products/{product_id}/moderate")
async def moderate_product(
    product_id: str,
    data: ModerateAction,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if data.action == "approve":
        product.status = ProductStatus.active
    elif data.action in ("reject", "archive"):
        product.status = ProductStatus.archived

    await db.commit()
    return {"message": f"Product {data.action}d"}


@router.get("/orders")
async def list_all_orders(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    query = select(Order)
    if status:
        query = query.where(Order.status == status)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    offset = (page - 1) * page_size
    result = await db.execute(query.order_by(Order.created_at.desc()).offset(offset).limit(page_size))
    orders = result.scalars().all()

    return {
        "items": [
            {
                "id": str(o.id),
                "customer_id": str(o.customer_id),
                "status": o.status,
                "total": float(o.total),
                "payment_status": o.payment_status,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ],
        "total": total,
    }


@router.get("/analytics")
async def platform_analytics(
    range: str = "30d",
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    from app.services.analytics_service import AnalyticsService
    range_map = {"7d": 7, "30d": 30, "90d": 90}
    days = range_map.get(range, 30)
    return await AnalyticsService(db).platform_analytics(days)


@router.get("/users")
async def list_users(
    page: int = 1,
    page_size: int = 50,
    role: str = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    from app.models.user import User as UserModel
    query = select(UserModel)
    if role:
        query = query.where(UserModel.role == role)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    offset = (page - 1) * page_size
    result = await db.execute(query.order_by(UserModel.created_at.desc()).offset(offset).limit(page_size))
    users = result.scalars().all()

    return {
        "items": [
            {
                "id": str(u.id),
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
        "total": total,
    }
