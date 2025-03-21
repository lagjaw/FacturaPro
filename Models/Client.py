from sqlalchemy import Column, String, Numeric, ForeignKey, Integer, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base

class Client(Base):
    __tablename__ = 'clients'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    status = Column(String, default='active')
    revenue = Column(Numeric, default=0)
    email = Column(String)
    address = Column(String)
    phone = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Fixed relationship name to match PaymentTransaction
    payment_transactions = relationship("PaymentTransaction", back_populates="client")
    invoices = relationship("Invoice", back_populates="client")  
