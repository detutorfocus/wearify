import uuid
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from app.core.types import CompatUUID as UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(150), unique=True, nullable=False, index=True)
    parent_id = Column(UUID(), ForeignKey("categories.id"), nullable=True)
    icon_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent")
    products = relationship("Product", back_populates="category")
