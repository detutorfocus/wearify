# app/api/v1/endpoints/cart.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])


class CartItemAdd(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None
    quantity: int = 1


class CartItemUpdate(BaseModel):
    quantity: int


@router.get("")
async def get_cart(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return await CartService(db).get_cart(current_user.id)


@router.post("/items", status_code=201)
async def add_to_cart(
    data: CartItemAdd,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await CartService(db).add_item(
        current_user.id, data.product_id, data.variant_id, data.quantity
    )
    await db.commit()
    return result


@router.put("/items/{item_id}")
async def update_cart_item(
    item_id: UUID,
    data: CartItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await CartService(db).update_item(current_user.id, item_id, data.quantity)
    await db.commit()
    return result


@router.delete("/items/{item_id}", status_code=204)
async def remove_from_cart(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await CartService(db).remove_item(current_user.id, item_id)
    await db.commit()


@router.delete("", status_code=204)
async def clear_cart(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await CartService(db).clear(current_user.id)
    await db.commit()
