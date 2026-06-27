import uuid
import enum
from sqlalchemy import Column, String, Numeric, Enum, ForeignKey
from app.core.types import CompatUUID as UUID, CompatJSON as JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class PaymentProvider(str, enum.Enum):
    paystack = "paystack"
    flutterwave = "flutterwave"
    stripe = "stripe"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
    refunded = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(), ForeignKey("orders.id"), nullable=False, index=True)
    provider = Column(Enum(PaymentProvider), nullable=False)
    provider_reference = Column(String(255), unique=True, nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), default="NGN")
    status = Column(Enum(PaymentStatus), default=PaymentStatus.pending, index=True)
    webhook_payload = Column(JSONB, default={})

    order = relationship("Order", back_populates="payment")
