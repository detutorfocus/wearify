"""
Cart service — business logic for cart management.
Handles add/update/remove/clear and snapshot pricing.
"""
from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.cart import CartItem
from app.models.product import Product, ProductVariant, ProductStatus


class CartService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_cart(self, customer_id: UUID) -> dict:
        result = await self.db.execute(
            select(CartItem)
            .options(
                selectinload(CartItem.product).selectinload(Product.images),
                selectinload(CartItem.variant),
            )
            .where(CartItem.customer_id == customer_id)
        )
        items = result.scalars().all()
        return self._serialize_cart(items)

    async def add_item(
        self,
        customer_id: UUID,
        product_id: UUID,
        variant_id: UUID | None,
        quantity: int,
    ) -> dict:
        # Validate product is active
        prod_result = await self.db.execute(
            select(Product)
            .options(selectinload(Product.images))
            .where(Product.id == product_id)
        )
        product = prod_result.scalar_one_or_none()
        if not product or product.status != ProductStatus.active:
            raise HTTPException(status_code=404, detail="Product not available")

        # Validate variant if given
        unit_price = Decimal(str(product.sale_price or product.base_price))
        if variant_id:
            var_result = await self.db.execute(
                select(ProductVariant).where(ProductVariant.id == variant_id)
            )
            variant = var_result.scalar_one_or_none()
            if variant:
                unit_price += Decimal(str(variant.additional_price))

        # Upsert: merge if same product+variant already in cart
        existing_result = await self.db.execute(
            select(CartItem).where(
                CartItem.customer_id == customer_id,
                CartItem.product_id == product_id,
                CartItem.variant_id == variant_id,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            existing.quantity += quantity
            existing.unit_price_snapshot = unit_price
        else:
            item = CartItem(
                customer_id=customer_id,
                product_id=product_id,
                variant_id=variant_id,
                quantity=quantity,
                unit_price_snapshot=unit_price,
            )
            self.db.add(item)

        await self.db.flush()
        return await self.get_cart(customer_id)

    async def update_item(self, customer_id: UUID, item_id: UUID, quantity: int) -> dict:
        result = await self.db.execute(
            select(CartItem).where(
                CartItem.id == item_id,
                CartItem.customer_id == customer_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Cart item not found")
        if quantity <= 0:
            await self.db.delete(item)
        else:
            item.quantity = quantity
        await self.db.flush()
        return await self.get_cart(customer_id)

    async def remove_item(self, customer_id: UUID, item_id: UUID) -> None:
        result = await self.db.execute(
            select(CartItem).where(
                CartItem.id == item_id,
                CartItem.customer_id == customer_id,
            )
        )
        item = result.scalar_one_or_none()
        if item:
            await self.db.delete(item)
            await self.db.flush()

    async def clear(self, customer_id: UUID) -> None:
        result = await self.db.execute(
            select(CartItem).where(CartItem.customer_id == customer_id)
        )
        for item in result.scalars().all():
            await self.db.delete(item)
        await self.db.flush()

    def _serialize_cart(self, items: list[CartItem]) -> dict:
        serialized = []
        subtotal = Decimal("0")
        for item in items:
            item_total = item.unit_price_snapshot * item.quantity
            subtotal += item_total
            serialized.append({
                "id": str(item.id),
                "product_id": str(item.product_id),
                "variant_id": str(item.variant_id) if item.variant_id else None,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price_snapshot),
                "subtotal": float(item_total),
                "product": {
                    "name": item.product.name,
                    "slug": item.product.slug,
                    "image_url": item.product.images[0].url
                    if item.product and item.product.images else None,
                } if item.product else None,
            })
        return {
            "items": serialized,
            "subtotal": float(subtotal),
            "total": float(subtotal),
            "item_count": sum(i.quantity for i in items),
        }
