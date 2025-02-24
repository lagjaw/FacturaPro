from sqlalchemy import Column, String, Numeric, ForeignKey, Integer, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base

class Alert(Base):
    __tablename__ = 'alerts'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String, nullable=False)
    message = Column(String, nullable=False)
    related_id = Column(String)
    related_type = Column(String, nullable=False)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
