import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Supplier(Base):
    __tablename__ = 'suppliers'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    contact_info = Column(String)
    created_at = Column(DateTime, default=func.now())

    products = relationship("Product", back_populates="supplier")
