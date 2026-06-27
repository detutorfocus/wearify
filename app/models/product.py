import uuid
import enum
from sqlalchemy import Column, String, Numeric, Integer, Boolean, Enum, ForeignKey, Text, TIMESTAMP
from app.core.types import CompatUUID as UUID, CompatArray as _ArrayText
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProductStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    archived = "archived"


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(), ForeignKey("vendors.id"), nullable=False, index=True)
    category_id = Column(UUID(), ForeignKey("categories.id"), nullable=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(300), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    base_price = Column(Numeric(12, 2), nullable=False)
    sale_price = Column(Numeric(12, 2), nullable=True)
    is_on_sale = Column(Boolean, default=False)
    flash_sale_end = Column(TIMESTAMP(timezone=True), nullable=True)
    sku = Column(String(100), unique=True, nullable=False)
    stock_quantity = Column(Integer, default=0)
    status = Column(Enum(ProductStatus), default=ProductStatus.draft, index=True)
    is_featured = Column(Boolean, default=False, index=True)
    tags = Column(_ArrayText(), default=[])
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)
    view_count = Column(Integer, default=0)

    vendor = relationship("Vendor", back_populates="products")
    category = relationship("Category", back_populates="products")
    images = relationship("ProductImage", back_populates="product",
                          order_by="ProductImage.sort_order",
                          cascade="all, delete-orphan")
    variants = relationship("ProductVariant", back_populates="product",
                            cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="product")


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(500), nullable=False)
    alt_text = Column(String(255), nullable=True)
    sort_order = Column(Integer, default=0)
    is_primary = Column(Boolean, default=False)

    product = relationship("Product", back_populates="images")


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    size = Column(String(20), nullable=True)
    color = Column(String(50), nullable=True)
    color_hex = Column(String(7), nullable=True)
    stock_quantity = Column(Integer, default=0)
    additional_price = Column(Numeric(10, 2), default=0.0)
    sku_variant = Column(String(150), nullable=True)

    product = relationship("Product", back_populates="variants")
