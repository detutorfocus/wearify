import uuid
import enum
from sqlalchemy import Column, String, Numeric, Enum, ForeignKey
from app.core.types import CompatUUID as UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class TransactionType(str, enum.Enum):
    credit = "credit"
    debit = "debit"
    withdrawal = "withdrawal"
    commission = "commission"


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(), ForeignKey("vendors.id"), nullable=False, unique=True)
    balance = Column(Numeric(14, 2), default=0.0)
    pending_balance = Column(Numeric(14, 2), default=0.0)
    total_earned = Column(Numeric(14, 2), default=0.0)
    total_withdrawn = Column(Numeric(14, 2), default=0.0)

    vendor = relationship("Vendor", back_populates="wallet")
    transactions = relationship("Transaction", back_populates="wallet")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(), ForeignKey("wallets.id"), nullable=False, index=True)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    balance_after = Column(Numeric(14, 2), nullable=False)
    reference = Column(String(255), nullable=True)
    description = Column(String(500), nullable=True)
    status = Column(String(50), default="completed")

    wallet = relationship("Wallet", back_populates="transactions")
