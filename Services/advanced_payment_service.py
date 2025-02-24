from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from Models.Check import Check
from Models.CheckDivision import CheckDivision
from Models.PaymentTransaction import PaymentTransaction
from Models.Alert import Alert
from Models.Invoice import Invoice


class AdvancedPaymentService:
    def __init__(self, db: Session):
        self.db = db

    async def divide_check(self, check_id: str, amounts: List[float]) -> Dict:
        """Diviser un chèque en plusieurs montants"""
        check = self.db.query(Check).filter(Check.id == check_id).first()
        if not check:
            raise ValueError("Chèque non trouvé")

        # Vérifier que la somme des divisions égale le montant du chèque
        if sum(amounts) != float(check.amount):
            raise ValueError("La somme des divisions doit être égale au montant du chèque")

        divisions = []
        for amount in amounts:
            division = CheckDivision(
                check_id=check_id,
                amount=amount,
                division_date=datetime.now(),
                status='pending'
            )
            self.db.add(division)
            divisions.append(division)

        # Créer une alerte pour la division
        alert = Alert(
            type='check_division',
            message=f"Chèque {check.check_number} divisé en {len(amounts)} parties",
            related_id=check.id,
            related_type='check',
            status='active'
        )
        self.db.add(alert)
        self.db.commit()

        return {
            "check_number": check.check_number,
            "total_amount": float(check.amount),
            "divisions": [
                {
                    "id": d.id,
                    "amount": float(d.amount),
                    "status": d.status
                } for d in divisions
            ]
        }

    async def replace_check(self, old_check_id: str, new_check_info: Dict) -> Dict:
        """Remplacer un chèque par un nouveau"""
        old_check = self.db.query(Check).filter(Check.id == old_check_id).first()
        if not old_check:
            raise ValueError("Chèque original non trouvé")

        # Créer le nouveau chèque
        new_check = Check(
            transaction_id=old_check.transaction_id,
            check_number=new_check_info['check_number'],
            amount=new_check_info['amount'],
            status='pending',
            check_date=datetime.now(),
            bank_name=new_check_info['bank_name'],
            bank_branch=new_check_info.get('bank_branch'),
            bank_account=new_check_info.get('bank_account'),
            swift_code=new_check_info.get('swift_code')
        )
        self.db.add(new_check)

        # Mettre à jour le statut de l'ancien chèque
        old_check.status = 'replaced'

        # Créer une alerte pour le remplacement
        alert = Alert(
            type='check_replacement',
            message=f"Chèque {old_check.check_number} remplacé par {new_check.check_number}",
            related_id=old_check.id,
            related_type='check',
            status='active'
        )
        self.db.add(alert)
        self.db.commit()

        return {
            "old_check": {
                "number": old_check.check_number,
                "amount": float(old_check.amount),
                "status": old_check.status
            },
            "new_check": {
                "number": new_check.check_number,
                "amount": float(new_check.amount),
                "status": new_check.status
            }
        }

    async def track_unpaid_checks(self, client_id: Optional[str] = None) -> List[Dict]:
        """Suivre les chèques impayés"""
        query = self.db.query(Check).filter(Check.status == 'unpaid')

        if client_id:
            query = query.join(PaymentTransaction).filter(
                PaymentTransaction.client_id == client_id
            )

        unpaid_checks = query.all()

        result = []
        for check in unpaid_checks:
            transaction = self.db.query(PaymentTransaction).filter(
                PaymentTransaction.id == check.transaction_id
            ).first()

            invoice = None
            if transaction:
                invoice = self.db.query(Invoice).filter(
                    Invoice.id == transaction.invoice_id
                ).first()

            result.append({
                "check_number": check.check_number,
                "amount": float(check.amount),
                "date": check.check_date,
                "bank_name": check.bank_name,
                "invoice_number": invoice.invoice_number if invoice else None,
                "days_overdue": (datetime.now() - check.check_date).days
            })

        return result

    async def process_check_payment(self, invoice_id: str, check_info: Dict) -> Dict:
        """Traiter un paiement par chèque avec support pour la division"""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Facture non trouvée")

        # Créer la transaction
        transaction = PaymentTransaction(
            client_id=invoice.client_id,
            invoice_id=invoice_id,
            amount=check_info['amount'],
            payment_method='check',
            status='pending',
            transaction_date=datetime.now()
        )
        self.db.add(transaction)
        self.db.flush()

        # Créer le chèque
        check = Check(
            transaction_id=transaction.id,
            check_number=check_info['check_number'],
            amount=check_info['amount'],
            status='pending',
            check_date=datetime.now(),
            bank_name=check_info['bank_name'],
            bank_branch=check_info.get('bank_branch'),
            bank_account=check_info.get('bank_account'),
            swift_code=check_info.get('swift_code')
        )
        self.db.add(check)

        # Si division demandée
        if 'divisions' in check_info:
            await self.divide_check(check.id, check_info['divisions'])

        self.db.commit()

        return {
            "transaction_id": transaction.id,
            "check_number": check.check_number,
            "amount": float(check.amount),
            "status": check.status
        }

    async def get_check_history(self, check_number: str) -> Dict:
        """Obtenir l'historique complet d'un chèque"""
        check = self.db.query(Check).filter(Check.check_number == check_number).first()
        if not check:
            raise ValueError("Chèque non trouvé")

        divisions = self.db.query(CheckDivision).filter(
            CheckDivision.check_id == check.id
        ).all()

        transaction = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.id == check.transaction_id
        ).first()

        return {
            "check_info": {
                "number": check.check_number,
                "amount": float(check.amount),
                "status": check.status,
                "bank_name": check.bank_name,
                "creation_date": check.created_at
            },
            "divisions": [
                {
                    "id": d.id,
                    "amount": float(d.amount),
                    "status": d.status,
                    "date": d.division_date
                } for d in divisions
            ],
            "transaction_info": {
                "id": transaction.id,
                "status": transaction.status,
                "date": transaction.transaction_date
            } if transaction else None
        }
