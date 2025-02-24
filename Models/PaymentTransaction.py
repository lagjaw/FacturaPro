import uuid
from sqlalchemy import Column, Integer, ForeignKey, Numeric, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class PaymentTransaction(Base):
    __tablename__ = 'payment_transactions'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey('clients.id'))
    invoice_id = Column(String, ForeignKey('invoices.id'))
    amount = Column(Numeric, nullable=False, default=0)
    transaction_date = Column(DateTime, default=func.now())
    payment_method = Column(String, nullable=False)
    status = Column(String, default='pending')
    due_date = Column(DateTime)
    paid_amount = Column(Numeric, default=0)
    remaining_amount = Column(Numeric, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Fixed relationships to match other models
    client = relationship("Client", back_populates="payment_transactions")
    invoice = relationship("Invoice", back_populates="payment_transactions")
    checks = relationship("Check", back_populates="payment_transaction")
