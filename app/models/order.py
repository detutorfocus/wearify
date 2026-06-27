import uuid
import enum
from sqlalchemy import Column, String, Numeric, Integer, Enum, ForeignKey, Text
from app.core.types import CompatUUID as UUID, CompatJSON as JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"
    refunded = "refunded"


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.pending, index=True)
    subtotal = Column(Numeric(12, 2), nullable=False)
    shipping_fee = Column(Numeric(10, 2), default=0.0)
    discount = Column(Numeric(10, 2), default=0.0)
    total = Column(Numeric(12, 2), nullable=False)
    shipping_address = Column(JSONB, nullable=False)
    payment_method = Column(String(50), nullable=True)
    payment_status = Column(String(50), default="pending", index=True)
    tracking_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    customer = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(), ForeignKey("orders.id"), nullable=False)
    product_id = Column(UUID(), ForeignKey("products.id"), nullable=False)
    vendor_id = Column(UUID(), ForeignKey("vendors.id"), nullable=False)
    variant_id = Column(UUID(), ForeignKey("product_variants.id"), nullable=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    vendor_commission = Column(Numeric(10, 2), default=0.0)
    vendor_earnings = Column(Numeric(10, 2), default=0.0)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    vendor = relationship("Vendor", back_populates="order_items")
