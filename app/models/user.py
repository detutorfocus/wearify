import uuid
import enum
from sqlalchemy import Column, String, Boolean, Enum
from app.core.types import CompatUUID as UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserRole(str, enum.Enum):
    customer = "customer"
    vendor = "vendor"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.customer, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    google_id = Column(String(255), nullable=True, unique=True)

    vendor_profile = relationship("Vendor", back_populates="user", uselist=False)
    orders = relationship("Order", back_populates="customer")
    reviews = relationship("Review", back_populates="customer")
    cart_items = relationship("CartItem", back_populates="customer")
    wishlist_items = relationship("WishlistItem", back_populates="customer")
    notifications = relationship("Notification", back_populates="user")
