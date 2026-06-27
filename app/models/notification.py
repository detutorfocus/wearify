import uuid
import enum
from sqlalchemy import Column, String, Boolean, Enum, ForeignKey, Text
from app.core.types import CompatUUID as UUID, CompatJSON as JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class NotificationType(str, enum.Enum):
    order_placed = "order_placed"
    order_shipped = "order_shipped"
    order_delivered = "order_delivered"
    payment_received = "payment_received"
    review_received = "review_received"
    vendor_approved = "vendor_approved"
    vendor_rejected = "vendor_rejected"
    low_stock = "low_stock"
    promotion = "promotion"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSONB, default={})
    is_read = Column(Boolean, default=False, index=True)

    user = relationship("User", back_populates="notifications")
