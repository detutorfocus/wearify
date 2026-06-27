import uuid
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Text
from app.core.types import CompatUUID as UUID, CompatArray as _ArrayText
from sqlalchemy.orm import relationship
from app.core.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(), ForeignKey("products.id"), nullable=False, index=True)
    customer_id = Column(UUID(), ForeignKey("users.id"), nullable=False, index=True)
    order_id = Column(UUID(), ForeignKey("orders.id"), nullable=True)
    rating = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    images = Column(_ArrayText(), default=[])
    is_verified_purchase = Column(Boolean, default=False)
    helpful_count = Column(Integer, default=0)
    is_approved = Column(Boolean, default=True)

    product = relationship("Product", back_populates="reviews")
    customer = relationship("User", back_populates="reviews")
