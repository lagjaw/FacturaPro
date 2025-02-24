from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from Models.PaymentTransaction import PaymentTransaction
from Models.Invoice import Invoice


class TransactionService:
    def __init__(self, db: Session):
        self.db = db

    async def create_transaction(
            self,
            client_id: str,
            invoice_id: str,
            amount: float,
            payment_method: str,
            due_date: datetime,
            transaction_date: Optional[datetime] = None,
            status: str = "Pending"
    ) -> Dict:
        """Create a new payment transaction"""
        try:
            # Fetch the invoice
            invoice = self.db.query(Invoice).filter_by(id=invoice_id).first()
            if not invoice:
                raise ValueError(f"Invoice with id {invoice_id} not found.")

            # Calculate remaining amount
            remaining_amount = invoice.total - amount

            # Default transaction date to current UTC time if not provided
            if not transaction_date:
                transaction_date = datetime.utcnow()

            # Create the transaction object
            transaction = PaymentTransaction(
                client_id=client_id,
                amount=amount,
                payment_method=payment_method,
                status=status,
                due_date=due_date,
                invoice_id=invoice_id,
                paid_amount=amount,
                remaining_amount=remaining_amount,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                transaction_date=transaction_date
            )

            self.db.add(transaction)
            self.db.commit()

            return {
                "id": transaction.id,
                "client_id": transaction.client_id,
                "invoice_id": transaction.invoice_id,
                "amount": float(transaction.amount),
                "payment_method": transaction.payment_method,
                "status": transaction.status,
                "due_date": transaction.due_date,
                "paid_amount": float(transaction.paid_amount),
                "remaining_amount": float(transaction.remaining_amount),
                "transaction_date": transaction.transaction_date
            }

        except SQLAlchemyError as e:
            self.db.rollback()
            raise ValueError(f"Database error: {str(e)}")
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to create transaction: {str(e)}")

    async def get_transaction(self, transaction_id: str) -> Dict:
        """Get transaction details by ID"""
        transaction = self.db.query(PaymentTransaction).filter_by(id=transaction_id).first()
        if not transaction:
            raise ValueError(f"Transaction with id {transaction_id} not found.")

        return {
            "id": transaction.id,
            "client_id": transaction.client_id,
            "invoice_id": transaction.invoice_id,
            "amount": float(transaction.amount),
            "payment_method": transaction.payment_method,
            "status": transaction.status,
            "due_date": transaction.due_date,
            "paid_amount": float(transaction.paid_amount),
            "remaining_amount": float(transaction.remaining_amount),
            "transaction_date": transaction.transaction_date,
            "created_at": transaction.created_at,
            "updated_at": transaction.updated_at
        }

    async def update_transaction_status(
            self,
            transaction_id: str,
            status: str,
            paid_amount: Optional[float] = None
    ) -> Dict:
        """Update transaction status and optionally paid amount"""
        transaction = self.db.query(PaymentTransaction).filter_by(id=transaction_id).first()
        if not transaction:
            raise ValueError(f"Transaction with id {transaction_id} not found.")

        transaction.status = status
        transaction.updated_at = datetime.utcnow()

        if paid_amount is not None:
            transaction.paid_amount = paid_amount
            transaction.remaining_amount = float(transaction.amount) - paid_amount

        try:
            self.db.commit()
            return await self.get_transaction(transaction_id)
        except SQLAlchemyError as e:
            self.db.rollback()
            raise ValueError(f"Database error: {str(e)}")

    async def get_client_transactions(
            self,
            client_id: str,
            status: Optional[str] = None,
            payment_method: Optional[str] = None,
            from_date: Optional[datetime] = None,
            to_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Get all transactions for a client with optional filters"""
        query = self.db.query(PaymentTransaction).filter_by(client_id=client_id)

        if status:
            query = query.filter(PaymentTransaction.status == status)
        if payment_method:
            query = query.filter(PaymentTransaction.payment_method == payment_method)
        if from_date:
            query = query.filter(PaymentTransaction.transaction_date >= from_date)
        if to_date:
            query = query.filter(PaymentTransaction.transaction_date <= to_date)

        transactions = query.all()

        return [{
            "id": t.id,
            "invoice_id": t.invoice_id,
            "amount": float(t.amount),
            "payment_method": t.payment_method,
            "status": t.status,
            "due_date": t.due_date,
            "paid_amount": float(t.paid_amount),
            "remaining_amount": float(t.remaining_amount),
            "transaction_date": t.transaction_date
        } for t in transactions]

    async def get_invoice_transactions(self, invoice_id: str) -> List[Dict]:
        """Get all transactions for an invoice"""
        transactions = self.db.query(PaymentTransaction).filter_by(invoice_id=invoice_id).all()

        return [{
            "id": t.id,
            "client_id": t.client_id,
            "amount": float(t.amount),
            "payment_method": t.payment_method,
            "status": t.status,
            "due_date": t.due_date,
            "paid_amount": float(t.paid_amount),
            "remaining_amount": float(t.remaining_amount),
            "transaction_date": t.transaction_date
        } for t in transactions]
