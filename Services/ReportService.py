from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from Models.Client import Client
from Models.Invoice import Invoice
from Models.Product import Product
from Models.Supplier import Supplier
from Models.PaymentTransaction import PaymentTransaction


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    async def generate_client_statement(self, client_id: str) -> Dict:
        """Generate a detailed statement for a client"""
        client = self.db.query(Client).get(client_id)
        if not client:
            raise ValueError(f"Client with id {client_id} not found")

        invoices = self.db.query(Invoice).filter_by(client_id=client_id).all()
        transactions = self.db.query(PaymentTransaction).filter_by(client_id=client_id).all()

        total_invoiced = sum(invoice.total for invoice in invoices)
        total_paid = sum(transaction.paid_amount for transaction in transactions)

        return {
            'client_info': {
                'id': client.id,
                'name': client.name,
                'email': client.email,
                'status': client.status
            },
            'summary': {
                'total_invoiced': float(total_invoiced),
                'total_paid': float(total_paid),
                'balance': float(total_paid - total_invoiced),
                'invoice_count': len(invoices),
                'transaction_count': len(transactions)
            },
            'invoices': [{
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'date': inv.date,
                'due_date': inv.due_date,
                'total': float(inv.total),
                'status': inv.status
            } for inv in invoices],
            'transactions': [{
                'id': trans.id,
                'date': trans.transaction_date,
                'amount': float(trans.amount),
                'method': trans.payment_method,
                'status': trans.status
            } for trans in transactions]
        }

    async def generate_supplier_report(self, supplier_id: str) -> Dict:
        """Generate a detailed report for a supplier"""
        supplier = self.db.query(Supplier).get(supplier_id)
        if not supplier:
            raise ValueError(f"Supplier with id {supplier_id} not found")

        products = self.db.query(Product).filter_by(supplier_id=supplier_id).all()

        # Calculate various metrics
        total_stock_value = sum(p.unit_price * p.stock_quantity for p in products)
        low_stock_products = [p for p in products if p.stock_quantity <= p.stock_alert_threshold]
        expired_products = [p for p in products if p.expiration_date and p.expiration_date < datetime.now()]

        return {
            'supplier_info': {
                'id': supplier.id,
                'name': supplier.name,
                'contact_info': supplier.contact_info
            },
            'summary': {
                'total_products': len(products),
                'total_stock_value': float(total_stock_value),
                'low_stock_count': len(low_stock_products),
                'expired_products_count': len(expired_products)
            },
            'products': [{
                'id': prod.id,
                'name': prod.name,
                'stock_quantity': prod.stock_quantity,
                'unit_price': float(prod.unit_price),
                'stock_value': float(prod.unit_price * prod.stock_quantity),
                'status': 'low_stock' if prod.stock_quantity <= prod.stock_alert_threshold else 'normal',
                'expiration_date': prod.expiration_date
            } for prod in products],
            'alerts': {
                'low_stock': [{
                    'product_id': p.id,
                    'name': p.name,
                    'current_stock': p.stock_quantity,
                    'threshold': p.stock_alert_threshold
                } for p in low_stock_products],
                'expired': [{
                    'product_id': p.id,
                    'name': p.name,
                    'expiration_date': p.expiration_date
                } for p in expired_products]
            }
        }

    async def generate_financial_summary(
            self,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
    ) -> Dict:
        """Generate a financial summary report"""
        query = self.db.query(Invoice)
        if start_date:
            query = query.filter(Invoice.date >= start_date)
        if end_date:
            query = query.filter(Invoice.date <= end_date)

        invoices = query.all()
        transactions = self.db.query(PaymentTransaction)

        if start_date:
            transactions = transactions.filter(PaymentTransaction.transaction_date >= start_date)
        if end_date:
            transactions = transactions.filter(PaymentTransaction.transaction_date <= end_date)

        transactions = transactions.all()

        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'invoices': {
                'total_count': len(invoices),
                'total_amount': float(sum(inv.total for inv in invoices)),
                'by_status': {
                    status: {
                        'count': len([i for i in invoices if i.status == status]),
                        'amount': float(sum(i.total for i in invoices if i.status == status))
                    }
                    for status in set(inv.status for inv in invoices)
                }
            },
            'payments': {
                'total_count': len(transactions),
                'total_amount': float(sum(t.amount for t in transactions)),
                'by_method': {
                    method: {
                        'count': len([t for t in transactions if t.payment_method == method]),
                        'amount': float(sum(t.amount for t in transactions if t.payment_method == method))
                    }
                    for method in set(t.payment_method for t in transactions)
                }
            }
        }
