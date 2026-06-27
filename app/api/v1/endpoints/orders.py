# app/api/v1/endpoints/orders.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_vendor, require_admin
from app.services.order_service import OrderService
from app.schemas.order import OrderCreate, OrderResponse, OrderListResponse

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create an order from the customer's cart.
    Validates stock availability, reserves inventory,
    and returns order with payment initialization URL.
    """
    service = OrderService(db)
    return await service.create_from_cart(
        customer_id=current_user.id,
        order_data=order_data,
    )


@router.get("", response_model=OrderListResponse)
async def list_my_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status: str = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = OrderService(db)
    return await service.list_customer_orders(
        customer_id=current_user.id,
        page=page,
        page_size=page_size,
        status_filter=status,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = OrderService(db)
    order = await service.get_by_id(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Only the order owner or admin can view
    if str(order["customer_id"]) != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    return order


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = OrderService(db)
    return await service.cancel_order(
        order_id=order_id,
        requesting_user=current_user,
    )


@router.put("/{order_id}/status")
async def update_order_status(
    order_id: UUID,
    new_status: str,
    tracking_number: str = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_vendor),
):
    """Vendors/admins update order status and add tracking info."""
    service = OrderService(db)
    return await service.update_status(
        order_id=order_id,
        new_status=new_status,
        tracking_number=tracking_number,
        requesting_user=current_user,
    )
