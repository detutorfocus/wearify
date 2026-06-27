# app/api/v1/endpoints/products.py
import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.redis import get_cached, set_cached, delete_pattern
from app.core.security import get_current_user, require_vendor
from app.services.product_service import ProductService
from app.services.storage_service import StorageService
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse,
    ProductListResponse, ProductDetailResponse,
)
from app.core.config import settings

router = APIRouter(prefix="/products", tags=["Products"])
limiter = Limiter(key_func=get_remote_address)


# ── Public Endpoints ──────────────────────────────────────────────────────────

@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    category: Optional[str] = None,
    vendor: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sizes: Optional[str] = None,           # comma-separated: "S,M,L"
    colors: Optional[str] = None,
    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc|popular)$"),
    in_stock: bool = False,
    on_sale: bool = False,
    db: AsyncSession = Depends(get_db),
):
    # Cache key based on all query params
    cache_key = f"products:list:{page}:{page_size}:{category}:{vendor}:{search}:{min_price}:{max_price}:{sizes}:{colors}:{sort}:{in_stock}:{on_sale}"

    cached = await get_cached(cache_key)
    if cached:
        return json.loads(cached)

    service = ProductService(db)
    result = await service.list_products(
        page=page, page_size=page_size,
        category_slug=category, vendor_slug=vendor,
        search=search, min_price=min_price, max_price=max_price,
        sizes=sizes.split(",") if sizes else None,
        colors=colors.split(",") if colors else None,
        sort=sort, in_stock=in_stock, on_sale=on_sale,
    )

    await set_cached(cache_key, json.dumps(result), ttl=300)  # 5-minute cache
    return result


@router.get("/featured", response_model=list[ProductResponse])
async def featured_products(
    limit: int = Query(8, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    cached = await get_cached("products:featured")
    if cached:
        return json.loads(cached)

    service = ProductService(db)
    products = await service.get_featured(limit=limit)
    await set_cached("products:featured", json.dumps(products), ttl=600)
    return products


@router.get("/flash-sale", response_model=list[ProductResponse])
async def flash_sale_products(db: AsyncSession = Depends(get_db)):
    service = ProductService(db)
    return await service.get_flash_sale_products()


@router.get("/{slug}", response_model=ProductDetailResponse)
async def get_product(slug: str, db: AsyncSession = Depends(get_db)):
    cache_key = f"products:detail:{slug}"
    cached = await get_cached(cache_key)
    if cached:
        return json.loads(cached)

    service = ProductService(db)
    product = await service.get_by_slug(slug)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Increment view count (fire-and-forget, don't await)
    import asyncio
    asyncio.create_task(service.increment_view(product["id"]))

    await set_cached(cache_key, json.dumps(product), ttl=300)
    return product


# ── Vendor Endpoints ──────────────────────────────────────────────────────────

@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_vendor),
):
    service = ProductService(db)
    product = await service.create_product(product_data, vendor_user_id=current_user.id)
    await delete_pattern("products:list:*")  # invalidate all listing caches
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_vendor),
):
    service = ProductService(db)
    product = await service.update_product(
        product_id=product_id,
        data=product_data,
        requesting_user=current_user,
    )
    await delete_pattern("products:*")
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_vendor),
):
    service = ProductService(db)
    await service.soft_delete(product_id, requesting_user=current_user)
    await delete_pattern("products:*")


@router.post("/{product_id}/images", response_model=list[dict])
async def upload_product_images(
    product_id: UUID,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_vendor),
):
    if len(files) > settings.MAX_PRODUCT_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.MAX_PRODUCT_IMAGES} images allowed"
        )

    storage = StorageService()
    product_service = ProductService(db)

    uploaded = []
    for file in files:
        if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large")

        url = await storage.upload_image(content, folder=f"products/{product_id}")
        img = await product_service.add_image(product_id, url, current_user)
        uploaded.append(img)

    await delete_pattern(f"products:*")
    return uploaded


# ── Categories ────────────────────────────────────────────────────────────────

@router.get("/categories/tree")
async def get_categories(db: AsyncSession = Depends(get_db)):
    cached = await get_cached("categories:tree")
    if cached:
        return json.loads(cached)

    service = ProductService(db)
    tree = await service.get_category_tree()
    await set_cached("categories:tree", json.dumps(tree), ttl=3600)  # 1-hour
    return tree
