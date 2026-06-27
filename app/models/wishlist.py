import uuid
from sqlalchemy import Column, ForeignKey
from app.core.types import CompatUUID as UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(), ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(UUID(), ForeignKey("products.id"), nullable=False)
    variant_id = Column(UUID(), ForeignKey("product_variants.id"), nullable=True)

    customer = relationship("User", back_populates="wishlist_items")
    product = relationship("Product")
