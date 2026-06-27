"""
Wishlist service — add, remove, list.
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.wishlist import WishlistItem
from app.models.product import Product


class WishlistService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_wishlist(self, customer_id: UUID) -> dict:
        result = await self.db.execute(
            select(WishlistItem)
            .options(selectinload(WishlistItem.product).selectinload(Product.images))
            .where(WishlistItem.customer_id == customer_id)
            .order_by(WishlistItem.created_at.desc())
        )
        items = result.scalars().all()
        return {
            "items": [
                {
                    "id": str(i.id),
                    "product_id": str(i.product_id),
                    "variant_id": str(i.variant_id) if i.variant_id else None,
                    "product": {
                        "name": i.product.name,
                        "slug": i.product.slug,
                        "base_price": float(i.product.base_price),
                        "sale_price": float(i.product.sale_price) if i.product.sale_price else None,
                        "is_on_sale": i.product.is_on_sale,
                        "stock_quantity": i.product.stock_quantity,
                        "image_url": i.product.images[0].url if i.product.images else None,
                    } if i.product else None,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                }
                for i in items
            ],
            "total": len(items),
        }

    async def add(
        self, customer_id: UUID, product_id: UUID, variant_id: UUID | None = None
    ) -> dict:
        # Check not already wishlisted
        existing = (await self.db.execute(
            select(WishlistItem).where(
                WishlistItem.customer_id == customer_id,
                WishlistItem.product_id == product_id,
            )
        )).scalar_one_or_none()
        if existing:
            return {"message": "Already in wishlist", "created": False}

        item = WishlistItem(
            customer_id=customer_id,
            product_id=product_id,
            variant_id=variant_id,
        )
        self.db.add(item)
        await self.db.flush()
        return {"message": "Added to wishlist", "created": True}

    async def remove(self, customer_id: UUID, product_id: UUID) -> bool:
        result = await self.db.execute(
            select(WishlistItem).where(
                WishlistItem.customer_id == customer_id,
                WishlistItem.product_id == product_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            return False
        await self.db.delete(item)
        await self.db.flush()
        return True

    async def is_wishlisted(self, customer_id: UUID, product_id: UUID) -> bool:
        result = await self.db.execute(
            select(WishlistItem).where(
                WishlistItem.customer_id == customer_id,
                WishlistItem.product_id == product_id,
            )
        )
        return result.scalar_one_or_none() is not None
