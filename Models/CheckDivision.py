from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base

class CheckDivision(Base):
    __tablename__ = 'check_divisions'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    check_id = Column(String, ForeignKey('checks.id'))
    amount = Column(Numeric, nullable=False, default=0)
    division_date = Column(DateTime, default=func.now())
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    check = relationship("Check", back_populates="check_divisions")
