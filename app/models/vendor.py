import uuid
import enum
from sqlalchemy import Column, String, Numeric, Integer, Boolean, Enum, ForeignKey, Text
from app.core.types import CompatUUID as UUID, CompatJSON as JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class KYCStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class SubscriptionPlan(str, enum.Enum):
    free = "free"
    starter = "starter"
    professional = "professional"
    enterprise = "enterprise"


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False)
    store_name = Column(String(255), unique=True, nullable=False)
    store_slug = Column(String(300), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    banner_url = Column(String(500), nullable=True)
    kyc_status = Column(Enum(KYCStatus), default=KYCStatus.pending, index=True)
    kyc_documents = Column(JSONB, default={})
    commission_rate = Column(Numeric(5, 2), default=10.0)
    subscription_plan = Column(Enum(SubscriptionPlan), default=SubscriptionPlan.free)
    is_featured = Column(Boolean, default=False, index=True)
    rating = Column(Numeric(3, 2), default=0.0)
    total_sales = Column(Integer, default=0)

    user = relationship("User", back_populates="vendor_profile")
    products = relationship("Product", back_populates="vendor")
    wallet = relationship("Wallet", back_populates="vendor", uselist=False)
    order_items = relationship("OrderItem", back_populates="vendor")
