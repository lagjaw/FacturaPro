from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging

from Models.Check import Check
from Models.CheckDivision import CheckDivision
from Models.Alert import Alert
from Models.PaymentTransaction import PaymentTransaction
from Models.Invoice import Invoice
from database import get_db_session

logger = logging.getLogger(__name__)

class AdvancedPaymentService:
    def __init__(self):
        pass

    async def divide_check(self, check_id: str, amounts: List[float]) -> Dict:
        """Diviser un chèque en plusieurs montants"""
        async with get_db_session() as session:
            try:
                async with session.begin():
                    # Retrieve the original check
                    result = await session.execute(
                        select(Check).filter(Check.id == check_id)
                    )
                    check = result.scalars().first()

                    if not check:
                        raise ValueError(f"Check {check_id} not found")

                    # Save original check details
                    check_number = check.check_number
                    check_amount = float(check.amount)
                    total_amount = sum(amounts)

                    # Validate that the total of the provided amounts matches the original check amount
                    if total_amount != check_amount:
                        raise ValueError(
                            f"Total divisions ({total_amount}) must equal the check amount ({check_amount})"
                        )

                    # Create divisions
                    divisions = []
                    for amount in amounts:
                        division = CheckDivision(
                            check_id=check_id,
                            amount=amount,
                            division_date=datetime.now(),
                            status='pending'
                        )
                        session.add(division)
                        divisions.append({
                            "id": division.id,
                            "amount": float(amount),
                            "status": 'pending'
                        })

                    # Create an alert
                    alert = Alert(
                        type='check_division',
                        message=f"Check {check_number} divided into {len(amounts)} parts",
                        related_id=check.id,
                        related_type='check',
                        status='active'
                    )
                    session.add(alert)

                    return {
                        "check_number": check_number,
                        "total_amount": check_amount,
                        "divisions": divisions
                    }
            except Exception as e:
                await session.rollback()
                logger.error(f"Check division error: {str(e)}", exc_info=True)
                raise
            finally:
                logger.info(f"Check {check_number} successfully divided")

    async def replace_check(self, old_check_id: str, new_check_info: Dict) -> Dict:
        """Remplacer un chèque par un nouveau"""
        async with get_db_session() as session:
            try:
                async with session.begin():
                    result = await session.execute(
                        select(Check).filter(Check.id == old_check_id))
                    old_check = result.scalars().first()

                    if not old_check:
                        raise ValueError(f"Original check {old_check_id} not found")

                    # Save original check details
                    old_number = old_check.check_number
                    old_amount = float(old_check.amount)

                    # Create new check
                    new_check = Check(
                        transaction_id=old_check.transaction_id,
                        check_number=new_check_info['check_number'],
                        amount=new_check_info['amount'],
                        status='pending',
                        check_date=datetime.now(),
                        bank_name=new_check_info['bank_name'],
                        **{k: v for k, v in new_check_info.items() 
                           if k in ['bank_branch', 'bank_account', 'swift_code']}
                    )
                    session.add(new_check)
                    await session.flush()  # Generate the ID

                    # Update the old check status
                    old_check.status = 'replaced'

                    # Create alert
                    alert = Alert(
                        type='check_replacement',
                        message=f"Check {old_number} replaced by {new_check.check_number}",
                        related_id=old_check.id,
                        related_type='check',
                        status='active'
                    )
                    session.add(alert)

                    return {
                        "old_check": {
                            "number": old_number,
                            "amount": old_amount,
                            "status": "replaced"
                        },
                        "new_check": {
                            "number": new_check.check_number,
                            "amount": float(new_check.amount),
                            "status": new_check.status
                        }
                    }
            except Exception as e:
                await session.rollback()
                logger.error(f"Check replacement error: {str(e)}", exc_info=True)
                raise
            finally:
                logger.info(f"Check {old_number} replaced successfully")

    async def process_check_payment(self, invoice_id: str, check_info: Dict) -> Dict:
        """Traiter un paiement par chèque"""
        async with get_db_session() as session:
            try:
                async with session.begin():
                    # Retrieve the invoice
                    result = await session.execute(
                        select(Invoice).filter(Invoice.id == invoice_id))
                    invoice = result.scalars().first()
                    
                    if not invoice:
                        raise ValueError("Invoice not found")

                    # Create the transaction
                    transaction = PaymentTransaction(
                        client_id=invoice.client_id,
                        invoice_id=invoice_id,
                        amount=check_info['amount'],
                        payment_method='check',
                        status='pending',
                        transaction_date=datetime.now()
                    )
                    session.add(transaction)
                    await session.flush()  # Generate the ID

                    # Create the check
                    check = Check(
                        transaction_id=transaction.id,
                        check_number=check_info['check_number'],
                        amount=check_info['amount'],
                        status='pending',
                        check_date=datetime.now(),
                        bank_name=check_info['bank_name'],
                        **{k: v for k, v in check_info.items() 
                           if k in ['bank_branch', 'bank_account', 'swift_code']}
                    )
                    session.add(check)
                    await session.flush()

                    # Handle divisions if necessary
                    if 'divisions' in check_info:
                        # Use the same session for the division
                        await self.divide_check(check.id, check_info['divisions'])

                    return {
                        "transaction_id": transaction.id,
                        "check_number": check.check_number,
                        "amount": float(check.amount),
                        "status": check.status
                    }
            except Exception as e:
                await session.rollback()
                logger.error(f"Payment processing error: {str(e)}", exc_info=True)
                raise
            finally:
                logger.info(f"Payment processed for invoice {invoice_id}")

    async def track_unpaid_checks(self, client_id: Optional[str] = None) -> List[Dict]:
        """Suivre les chèques impayés"""
        async with get_db_session() as session:
            try:
                query = select(Check).filter(Check.status == 'unpaid')
                
                if client_id:
                    query = query.join(PaymentTransaction).filter(
                        PaymentTransaction.client_id == client_id
                    )

                result = await session.execute(query)
                checks = result.scalars().all()

                response = []
                for check in checks:
                    # Retrieve related information
                    transaction = (await session.execute(
                        select(PaymentTransaction)
                        .filter(PaymentTransaction.id == check.transaction_id)
                    )).scalars().first()

                    invoice = (await session.execute(
                        select(Invoice)
                        .filter(Invoice.id == transaction.invoice_id)
                    )).scalars().first() if transaction else None

                    response.append({
                        "check_number": check.check_number,
                        "amount": float(check.amount),
                        "date": check.check_date.isoformat(),
                        "bank_name": check.bank_name,
                        "invoice_number": invoice.invoice_number if invoice else None,
                        "days_overdue": (datetime.now() - check.check_date).days
                    })

                return response
            except Exception as e:
                logger.error(f"Unpaid checks error: {str(e)}", exc_info=True)
                raise

    async def get_check_history(self, check_number: str) -> Dict:
        """Historique complet d'un chèque"""
        async with get_db_session() as session:
            try:
                result = await session.execute(
                    select(Check).filter(Check.check_number == check_number))
                check = result.scalars().first()

                if not check:
                    raise ValueError("Check not found")

                # Retrieve divisions
                divisions = (await session.execute(
                    select(CheckDivision)
                    .filter(CheckDivision.check_id == check.id)
                )).scalars().all()

                # Retrieve associated transaction
                transaction = (await session.execute(
                    select(PaymentTransaction)
                    .filter(PaymentTransaction.id == check.transaction_id)
                )).scalars().first()

                return {
                    "check_info": {
                        "number": check.check_number,
                        "amount": float(check.amount),
                        "status": check.status,
                        "bank_name": check.bank_name,
                        "creation_date": check.created_at.isoformat()
                    },
                    "divisions": [{
                        "id": d.id,
                        "amount": float(d.amount),
                        "status": d.status,
                        "date": d.division_date.isoformat()
                    } for d in divisions],
                    "transaction_info": {
                        "id": transaction.id,
                        "status": transaction.status,
                        "date": transaction.transaction_date.isoformat()
                    } if transaction else None
                }
            except Exception as e:
                logger.error(f"Check history error: {str(e)}", exc_info=True)
                raise