from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base

class Check(Base):
    __tablename__ = 'checks'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String, ForeignKey('payment_transactions.id'))
    check_number = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False, default=0)
    status = Column(String, default='pending')
    check_date = Column(DateTime, nullable=False)
    bank_name = Column(String, nullable=False)
    bank_branch = Column(String)
    bank_account = Column(String)
    swift_code = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Fixed relationship name to match PaymentTransaction model
    payment_transaction = relationship("PaymentTransaction", back_populates="checks")
    check_divisions = relationship("CheckDivision", back_populates="check")
