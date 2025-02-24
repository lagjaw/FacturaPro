from sqlalchemy import Column, String, Numeric, ForeignKey, Integer, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base

class InvoiceProduct(Base):
    __tablename__ = 'invoice_products'

    invoice_id = Column(String, ForeignKey('invoices.id'), primary_key=True)
    product_id = Column(String, ForeignKey('products.id'), primary_key=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric, nullable=False, default=0)
    total_price = Column(Numeric, nullable=False, default=0)
    created_at = Column(DateTime, default=func.now())

    invoice = relationship("Invoice", back_populates="invoice_products")
    product = relationship("Product", back_populates="invoice_products")
