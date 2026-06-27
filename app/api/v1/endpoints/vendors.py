from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_vendor
from app.services.vendor_service import VendorService
from app.schemas.vendor import VendorRegister, VendorProfileUpdate, WithdrawalRequest

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.post("/register", status_code=201)
async def register_vendor(
    data: VendorRegister,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = VendorService(db)
    vendor = await service.register(data, current_user.id)
    await db.commit()
    return vendor


@router.get("/{slug}")
async def get_vendor_storefront(slug: str, db: AsyncSession = Depends(get_db)):
    service = VendorService(db)
    vendor = await service.get_by_slug(slug)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.get("/me/dashboard")
async def vendor_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_vendor),
):
    service = VendorService(db)
    return await service.get_dashboard_stats(current_user.id)


@router.get("/me/products")
async def vendor_products(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_vendor),
):
    from app.services.product_service import ProductService
    from app.models.vendor import Vendor
    from sqlalchemy import select

    vendor_result = await db.execute(select(Vendor).where(Vendor.user_id == current_user.id))
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    service = ProductService(db)
    return await service.list_products(
        page=page, page_size=page_size, vendor_slug=vendor.store_slug
    )


@router.get("/me/wallet")
async def vendor_wallet(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_vendor),
):
    from app.models.vendor import Vendor
    from app.models.wallet import Wallet, Transaction
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    vendor_result = await db.execute(select(Vendor).where(Vendor.user_id == current_user.id))
    vendor = vendor_result.scalar_one_or_none()

    wallet_result = await db.execute(
        select(Wallet)
        .options(selectinload(Wallet.transactions))
        .where(Wallet.vendor_id == vendor.id)
    )
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    return {
        "balance": float(wallet.balance),
        "pending_balance": float(wallet.pending_balance),
        "total_earned": float(wallet.total_earned),
        "total_withdrawn": float(wallet.total_withdrawn),
        "transactions": [
            {
                "id": str(t.id),
                "type": t.type,
                "amount": float(t.amount),
                "balance_after": float(t.balance_after),
                "description": t.description,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
            }
            for t in sorted(wallet.transactions, key=lambda x: x.created_at, reverse=True)[:50]
        ],
    }


@router.post("/me/withdraw")
async def request_withdrawal(
    data: WithdrawalRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_vendor),
):
    from app.models.vendor import Vendor
    from app.models.wallet import Wallet, Transaction, TransactionType
    from sqlalchemy import select
    from app.core.config import settings

    vendor_result = await db.execute(select(Vendor).where(Vendor.user_id == current_user.id))
    vendor = vendor_result.scalar_one_or_none()

    wallet_result = await db.execute(select(Wallet).where(Wallet.vendor_id == vendor.id))
    wallet = wallet_result.scalar_one_or_none()

    if float(data.amount) < settings.MIN_WITHDRAWAL_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum withdrawal is {settings.MIN_WITHDRAWAL_AMOUNT}"
        )
    if float(wallet.balance) < float(data.amount):
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")

    wallet.balance -= data.amount
    wallet.total_withdrawn += data.amount

    txn = Transaction(
        wallet_id=wallet.id,
        type=TransactionType.withdrawal,
        amount=data.amount,
        balance_after=wallet.balance,
        description=f"Withdrawal to {data.account_number}",
        status="pending",
    )
    db.add(txn)
    await db.commit()
    return {"message": "Withdrawal request submitted", "transaction_id": str(txn.id)}


@router.put("/me/profile")
async def update_vendor_profile(
    data: VendorProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_vendor),
):
    from app.models.vendor import Vendor
    from sqlalchemy import select

    result = await db.execute(select(Vendor).where(Vendor.user_id == current_user.id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(vendor, key, value)

    await db.commit()
    return {"message": "Profile updated"}


@router.get("/me/analytics")
async def vendor_analytics(
    range: str = "30d",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_vendor),
):
    """Vendor sales analytics for the given time range (7d, 30d, 90d)."""
    from app.services.analytics_service import AnalyticsService
    from app.models.vendor import Vendor
    from sqlalchemy import select

    vendor_result = await db.execute(select(Vendor).where(Vendor.user_id == current_user.id))
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    range_map = {"7d": 7, "30d": 30, "90d": 90}
    days = range_map.get(range, 30)
    return await AnalyticsService(db).vendor_analytics(vendor.id, days)
