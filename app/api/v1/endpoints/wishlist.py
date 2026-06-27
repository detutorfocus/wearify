# app/api/v1/endpoints/wishlist.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.wishlist_service import WishlistService

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


class WishlistAdd(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None


@router.get("")
async def get_wishlist(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return await WishlistService(db).get_wishlist(current_user.id)


@router.post("", status_code=201)
async def add_to_wishlist(
    data: WishlistAdd,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await WishlistService(db).add(current_user.id, data.product_id, data.variant_id)
    await db.commit()
    return result


@router.delete("/{product_id}", status_code=204)
async def remove_from_wishlist(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await WishlistService(db).remove(current_user.id, product_id)
    await db.commit()
