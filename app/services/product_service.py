import math
import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update
from sqlalchemy.orm import selectinload

from app.models.product import Product, ProductImage, ProductStatus
from app.models.vendor import Vendor
from app.models.category import Category
from app.schemas.product import ProductCreate, ProductUpdate
from app.utils.helpers import generate_slug, generate_sku


class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_products(
        self,
        page: int = 1,
        page_size: int = 20,
        category_slug: Optional[str] = None,
        vendor_slug: Optional[str] = None,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sizes: Optional[list] = None,
        colors: Optional[list] = None,
        sort: str = "newest",
        in_stock: bool = False,
        on_sale: bool = False,
    ) -> dict:
        query = (
            select(Product)
            .options(selectinload(Product.images), selectinload(Product.vendor))
            .where(Product.status == ProductStatus.active)
        )

        if search:
            query = query.where(
                or_(
                    Product.name.ilike(f"%{search}%"),
                    Product.description.ilike(f"%{search}%"),
                )
            )
        if category_slug:
            query = query.join(Category).where(Category.slug == category_slug)
        if vendor_slug:
            query = query.join(Vendor).where(Vendor.store_slug == vendor_slug)
        if min_price is not None:
            query = query.where(Product.base_price >= min_price)
        if max_price is not None:
            query = query.where(Product.base_price <= max_price)
        if in_stock:
            query = query.where(Product.stock_quantity > 0)
        if on_sale:
            query = query.where(Product.is_on_sale == True)

        sort_map = {
            "newest": Product.created_at.desc(),
            "price_asc": Product.base_price.asc(),
            "price_desc": Product.base_price.desc(),
            "popular": Product.view_count.desc(),
        }
        query = query.order_by(sort_map.get(sort, Product.created_at.desc()))

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await self.db.execute(query)
        products = result.scalars().all()

        return {
            "items": [self._serialize(p) for p in products],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": math.ceil(total / page_size),
        }

    async def get_by_slug(self, slug: str) -> dict | None:
        result = await self.db.execute(
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.variants),
                selectinload(Product.vendor),
                selectinload(Product.reviews),
            )
            .where(Product.slug == slug, Product.status == ProductStatus.active)
        )
        product = result.scalar_one_or_none()
        return self._serialize(product, detail=True) if product else None

    async def get_featured(self, limit: int = 8) -> list:
        result = await self.db.execute(
            select(Product)
            .options(selectinload(Product.images), selectinload(Product.vendor))
            .where(Product.is_featured == True, Product.status == ProductStatus.active)
            .order_by(Product.created_at.desc())
            .limit(limit)
        )
        return [self._serialize(p) for p in result.scalars().all()]

    async def get_flash_sale_products(self) -> list:
        from datetime import datetime, timezone
        result = await self.db.execute(
            select(Product)
            .options(selectinload(Product.images), selectinload(Product.vendor))
            .where(
                Product.is_on_sale == True,
                Product.flash_sale_end > datetime.now(timezone.utc),
                Product.status == ProductStatus.active,
            )
            .order_by(Product.flash_sale_end.asc())
        )
        return [self._serialize(p) for p in result.scalars().all()]

    async def create_product(self, data: ProductCreate, vendor_user_id: UUID) -> dict:
        # Get vendor from user id
        result = await self.db.execute(
            select(Vendor).where(Vendor.user_id == vendor_user_id)
        )
        vendor = result.scalar_one_or_none()
        if not vendor:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Vendor profile not found")

        slug = await self._unique_slug(data.name)
        sku = generate_sku(vendor.store_slug, data.name)

        product = Product(
            vendor_id=vendor.id,
            category_id=data.category_id,
            name=data.name,
            slug=slug,
            description=data.description,
            base_price=data.base_price,
            sale_price=data.sale_price,
            is_on_sale=data.is_on_sale,
            sku=sku,
            stock_quantity=data.stock_quantity,
            tags=data.tags,
            meta_title=data.meta_title,
            meta_description=data.meta_description,
        )
        self.db.add(product)
        await self.db.flush()
        # Re-fetch with eager-loaded relationships to avoid lazy-load in _serialize
        result = await self.db.execute(
            select(Product)
            .options(selectinload(Product.images), selectinload(Product.vendor))
            .where(Product.id == product.id)
        )
        product = result.scalar_one()
        return self._serialize(product)

    async def update_product(self, product_id: UUID, data: ProductUpdate, requesting_user) -> dict:
        product = await self._get_product_for_user(product_id, requesting_user)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(product, key, value)
        await self.db.flush()
        return self._serialize(product)

    async def soft_delete(self, product_id: UUID, requesting_user) -> None:
        product = await self._get_product_for_user(product_id, requesting_user)
        product.status = ProductStatus.archived
        await self.db.flush()

    async def add_image(self, product_id: UUID, url: str, requesting_user) -> dict:
        product = await self._get_product_for_user(product_id, requesting_user)
        existing_count = len(product.images) if product.images else 0
        image = ProductImage(
            product_id=product_id,
            url=url,
            sort_order=existing_count,
            is_primary=(existing_count == 0),
        )
        self.db.add(image)
        await self.db.flush()
        return {"id": str(image.id), "url": image.url, "is_primary": image.is_primary}

    async def increment_view(self, product_id: str) -> None:
        await self.db.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(view_count=Product.view_count + 1)
        )
        await self.db.commit()

    async def get_category_tree(self) -> list:
        result = await self.db.execute(
            select(Category)
            .options(selectinload(Category.children))
            .where(Category.parent_id == None, Category.is_active == True)
            .order_by(Category.sort_order)
        )
        categories = result.scalars().all()
        return [self._serialize_category(c) for c in categories]

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _unique_slug(self, name: str) -> str:
        base = generate_slug(name)
        slug = base
        counter = 1
        while True:
            exists = await self.db.execute(select(Product).where(Product.slug == slug))
            if not exists.scalar_one_or_none():
                return slug
            slug = f"{base}-{counter}"
            counter += 1

    async def _get_product_for_user(self, product_id: UUID, user) -> Product:
        from fastapi import HTTPException
        result = await self.db.execute(
            select(Product)
            .options(selectinload(Product.images), selectinload(Product.vendor))
            .where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if user.role != "admin" and str(product.vendor.user_id) != str(user.id):
            raise HTTPException(status_code=403, detail="Not your product")
        return product

    def _serialize(self, product: Product, detail: bool = False) -> dict:
        if not product:
            return None
        data = {
            "id": str(product.id),
            "name": product.name,
            "slug": product.slug,
            "base_price": float(product.base_price),
            "sale_price": float(product.sale_price) if product.sale_price else None,
            "is_on_sale": product.is_on_sale,
            "sku": product.sku,
            "stock_quantity": product.stock_quantity,
            "status": product.status,
            "is_featured": product.is_featured,
            "view_count": product.view_count,
            "images": [{"id": str(i.id), "url": i.url, "is_primary": i.is_primary, "sort_order": i.sort_order} for i in (product.images or [])],
            "vendor": {
                "id": str(product.vendor.id),
                "store_name": product.vendor.store_name,
                "store_slug": product.vendor.store_slug,
                "logo_url": product.vendor.logo_url,
                "rating": float(product.vendor.rating),
            } if product.vendor else None,
            "created_at": product.created_at.isoformat() if product.created_at else None,
        }
        if detail:
            data.update({
                "description": product.description,
                "tags": product.tags or [],
                "variants": [
                    {
                        "id": str(v.id),
                        "size": v.size,
                        "color": v.color,
                        "color_hex": v.color_hex,
                        "stock_quantity": v.stock_quantity,
                        "additional_price": float(v.additional_price),
                    }
                    for v in (product.variants or [])
                ],
                "meta_title": product.meta_title,
                "meta_description": product.meta_description,
            })
        return data

    def _serialize_category(self, cat: Category) -> dict:
        return {
            "id": str(cat.id),
            "name": cat.name,
            "slug": cat.slug,
            "icon_url": cat.icon_url,
            "image_url": cat.image_url,
            "children": [self._serialize_category(c) for c in (cat.children or [])],
        }
