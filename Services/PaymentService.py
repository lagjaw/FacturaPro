from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from Models import Invoice
from Models.Alert import Alert
from Models.Check import Check
from Models.CheckDivision import CheckDivision
from Models.PaymentTransaction import PaymentTransaction


class PaymentService:
    def __init__(self, db: Session):
        self.db = db

    async def process_payment(self, invoice_id: str, payment_method: str, amount: float) -> Dict:
        """Process a new payment with support for check divisions"""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Invoice not found")

        # Create payment transaction
        transaction = PaymentTransaction(
            client_id=invoice.client_id,
            invoice_id=invoice_id,
            amount=amount,
            payment_method=payment_method,
            status='completed' if amount >= invoice.total else 'partial',
            transaction_date=datetime.now(),
            paid_amount=amount,
            remaining_amount=invoice.total - amount
        )

        # Handle check payments
        if payment_method == 'check':
            check = await self._process_check(transaction, amount)
            transaction.checks.append(check)

        # Update invoice status
        invoice.status = transaction.status

        self.db.add(transaction)
        self.db.commit()

        return {
            "transaction_id": transaction.id,
            "status": transaction.status,
            "amount": amount,
            "remaining": transaction.remaining_amount
        }

    async def _process_check(self, transaction: PaymentTransaction, amount: float) -> Check:
        """Process check payment with automatic division if needed"""
        check = Check(
            transaction_id=transaction.id,
            check_number=self._generate_check_number(),
            amount=amount,
            status='pending',
            check_date=datetime.now()
        )

        # Automatically divide checks over 10000
        if amount > 10000:
            await self._divide_check(check, amount)

        return check

    async def _divide_check(self, check: Check, total_amount: float) -> None:
        """Divide large checks into smaller amounts"""
        remaining = total_amount
        division_amount = 5000  # Standard division amount

        while remaining > 0:
            current_amount = min(remaining, division_amount)
            division = CheckDivision(
                check_id=check.id,
                amount=current_amount,
                division_date=datetime.now(),
                status='pending'
            )
            check.check_divisions.append(division)
            remaining -= current_amount

    async def handle_check_replacement(self, old_check_id: str, new_check_info: Dict) -> Dict:
        """Handle replacement of a bounced check"""
        old_check = self.db.query(Check).filter(Check.id == old_check_id).first()
        if not old_check:
            raise ValueError("Original check not found")

        # Create new check
        new_check = Check(
            transaction_id=old_check.transaction_id,
            check_number=self._generate_check_number(),
            amount=new_check_info['amount'],
            status='pending',
            check_date=datetime.now(),
            bank_name=new_check_info.get('bank_name'),
            bank_branch=new_check_info.get('bank_branch'),
            bank_account=new_check_info.get('bank_account'),
            swift_code=new_check_info.get('swift_code')
        )

        # Update old check status
        old_check.status = 'replaced'

        # Create alert for check replacement
        alert = Alert(
            type='check_replacement',
            message=f"Check {old_check.check_number} has been replaced with {new_check.check_number}",
            related_id=old_check.transaction_id,
            related_type='transaction',
            status='active'
        )

        self.db.add_all([new_check, alert])
        self.db.commit()

        return {
            "old_check": old_check.check_number,
            "new_check": new_check.check_number,
            "status": "replaced",
            "amount": new_check.amount
        }

    async def get_payment_status(self, invoice_id: str) -> Dict:
        """Get payment status for an invoice"""
        transactions = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.invoice_id == invoice_id
        ).all()

        total_paid = sum(t.paid_amount for t in transactions)
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()

        return {
            "invoice_id": invoice_id,
            "total_amount": invoice.total if invoice else 0,
            "paid_amount": total_paid,
            "remaining_amount": (invoice.total - total_paid) if invoice else 0,
            "status": invoice.status if invoice else 'unknown',
            "transactions": [
                {
                    "id": t.id,
                    "amount": t.amount,
                    "method": t.payment_method,
                    "date": t.transaction_date,
                    "status": t.status
                } for t in transactions
            ]
        }

    def _generate_check_number(self) -> str:
        """Generate a unique check number"""
        return f"CHK-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    async def list_transactions(
            self,
            client_id: Optional[str] = None,
            payment_method: Optional[str] = None,
            status: Optional[str] = None,
            from_date: Optional[datetime] = None,
            to_date: Optional[datetime] = None
    ) -> List[Dict]:
        """List payment transactions with filters"""
        query = self.db.query(PaymentTransaction)

        if client_id:
            query = query.filter(PaymentTransaction.client_id == client_id)
        if payment_method:
            query = query.filter(PaymentTransaction.payment_method == payment_method)
        if status:
            query = query.filter(PaymentTransaction.status == status)
        if from_date:
            query = query.filter(PaymentTransaction.transaction_date >= from_date)
        if to_date:
            query = query.filter(PaymentTransaction.transaction_date <= to_date)

        transactions = query.all()

        return [
            {
                "id": t.id,
                "client_id": t.client_id,
                "invoice_id": t.invoice_id,
                "amount": float(t.amount),
                "payment_method": t.payment_method,
                "status": t.status,
                "transaction_date": t.transaction_date,
                "paid_amount": float(t.paid_amount),
                "remaining_amount": float(t.remaining_amount)
            }
            for t in transactions
        ]

    async def list_pending_checks(
            self,
            client_id: Optional[str] = None,
            from_date: Optional[datetime] = None,
            to_date: Optional[datetime] = None
    ) -> List[Dict]:
        """List pending checks with filters"""
        query = self.db.query(Check).filter(Check.status == 'pending')

        if client_id:
            query = query.join(PaymentTransaction).filter(
                PaymentTransaction.client_id == client_id
            )
        if from_date:
            query = query.filter(Check.check_date >= from_date)
        if to_date:
            query = query.filter(Check.check_date <= to_date)

        checks = query.all()

        return [
            {
                "id": c.id,
                "check_number": c.check_number,
                "amount": float(c.amount),
                "check_date": c.check_date,
                "bank_name": c.bank_name,
                "bank_branch": c.bank_branch,
                "transaction_id": c.transaction_id,
                "client_info": {
                    "id": c.paymenttransaction.client_id,
                    "name": c.paymenttransaction.client.name
                } if c.paymenttransaction and c.paymenttransaction.client else None
            }
            for c in checks
        ]
