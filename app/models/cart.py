import uuid
from sqlalchemy import Column, Integer, Numeric, ForeignKey
from app.core.types import CompatUUID as UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(), ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(UUID(), ForeignKey("products.id"), nullable=False)
    variant_id = Column(UUID(), ForeignKey("product_variants.id"), nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price_snapshot = Column(Numeric(12, 2), nullable=False)

    customer = relationship("User", back_populates="cart_items")
    product = relationship("Product")
    variant = relationship("ProductVariant")
