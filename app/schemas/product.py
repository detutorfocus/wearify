from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.models.product import ProductStatus


class ProductImageSchema(BaseModel):
    id: UUID
    url: str
    alt_text: str | None
    sort_order: int
    is_primary: bool
    model_config = {"from_attributes": True}


class ProductVariantSchema(BaseModel):
    id: UUID
    size: str | None
    color: str | None
    color_hex: str | None
    stock_quantity: int
    additional_price: Decimal
    sku_variant: str | None
    model_config = {"from_attributes": True}


class VendorBriefSchema(BaseModel):
    id: UUID
    store_name: str
    store_slug: str
    logo_url: str | None
    rating: Decimal
    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    base_price: Decimal
    sale_price: Decimal | None = None
    is_on_sale: bool = False
    category_id: UUID | None = None
    stock_quantity: int = 0
    tags: list[str] = []
    meta_title: str | None = None
    meta_description: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    base_price: Decimal | None = None
    sale_price: Decimal | None = None
    is_on_sale: bool | None = None
    stock_quantity: int | None = None
    status: ProductStatus | None = None
    is_featured: bool | None = None
    tags: list[str] | None = None


class ProductResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    base_price: Decimal
    sale_price: Decimal | None
    is_on_sale: bool
    sku: str
    stock_quantity: int
    status: ProductStatus
    is_featured: bool
    view_count: int
    images: list[ProductImageSchema] = []
    vendor: VendorBriefSchema | None
    created_at: datetime
    model_config = {"from_attributes": True}


class ProductDetailResponse(ProductResponse):
    description: str | None
    tags: list[str]
    variants: list[ProductVariantSchema] = []
    meta_title: str | None
    meta_description: str | None


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    pages: int
