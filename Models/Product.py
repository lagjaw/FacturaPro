import uuid
from sqlalchemy import Column, Integer, ForeignKey, Numeric, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy import func
from database import Base

class Product(Base):
    __tablename__ = 'products'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    stock_quantity = Column(Integer, default=0)
    unit_price = Column(Numeric, nullable=False, default=0)
    expiration_date = Column(DateTime)
    stock_alert_threshold = Column(Integer, default=10)
    expiration_alert_threshold = Column(Integer, default=30)
    description = Column(String)
    category_id = Column(String, ForeignKey('categories.id'))
    supplier_id = Column(String, ForeignKey('suppliers.id'))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    category = relationship("Category", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    invoice_products = relationship("InvoiceProduct", back_populates="product")
