import uuid
from sqlalchemy import Column, String, DateTime, Numeric, Text, ForeignKey  # Import ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import json

class Invoice(Base):
    __tablename__ = 'invoices'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_number = Column(String, unique=True, nullable=False)
    date = Column(DateTime, default=func.now())
    due_date = Column(DateTime, nullable=False)
    bill_to = Column(String, nullable=False)
    total = Column(Numeric, default=0)
    subtotal = Column(Numeric, default=0)
    tax = Column(Numeric, default=0)
    gstin = Column(String, nullable=True)
    discount = Column(Numeric, default=0)
    bank_name = Column(String, nullable=True)
    branch_name = Column(String, nullable=True)
    bank_account_number = Column(String, nullable=True)
    bank_swift_code = Column(String, nullable=True)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    items = Column(Text, nullable=True)

    client_id = Column(String, ForeignKey('clients.id'), nullable=False)

    # Relationships
    payment_transactions = relationship("PaymentTransaction", back_populates="invoice")
    invoice_products = relationship("InvoiceProduct", back_populates="invoice")
    client = relationship("Client", back_populates="invoices")  # Define the relationship

    def set_items(self, items_data):
        """Stocke les items sous format JSON"""
        self.items = json.dumps(items_data)

    def get_items(self):
        """Récupère les items en tant qu'objet JSON"""
        return json.loads(self.items) if self.items else []