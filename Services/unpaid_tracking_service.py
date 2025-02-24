from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from Models.Invoice import Invoice
from Models.PaymentTransaction import PaymentTransaction
from Models.Check import Check
from Models.Alert import Alert
from Models.Client import Client


class UnpaidTrackingService:
    def __init__(self, db: Session):
        self.db = db

    async def track_unpaid_invoices(self, days_overdue: int = 30) -> List[Dict]:
        """Suivre les factures impayées dépassant un certain nombre de jours"""
        threshold_date = datetime.now() - timedelta(days=days_overdue)

        unpaid_invoices = self.db.query(Invoice).filter(
            and_(
                Invoice.status != 'paid',
                Invoice.due_date <= threshold_date
            )
        ).all()

        result = []
        for invoice in unpaid_invoices:
            # Calculer le montant déjà payé
            paid_amount = self.db.query(PaymentTransaction).filter(
                and_(
                    PaymentTransaction.invoice_id == invoice.id,
                    PaymentTransaction.status == 'completed'
                )
            ).with_entities(func.sum(PaymentTransaction.amount)).scalar() or 0

            remaining_amount = float(invoice.total) - float(paid_amount)

            # Récupérer les informations du client
            client = self.db.query(Client).filter(Client.id == invoice.client_id).first()

            result.append({
                "invoice_number": invoice.invoice_number,
                "client_name": client.name if client else "Unknown",
                "total_amount": float(invoice.total),
                "paid_amount": float(paid_amount),
                "remaining_amount": remaining_amount,
                "due_date": invoice.due_date,
                "days_overdue": (datetime.now() - invoice.due_date).days,
                "status": invoice.status
            })

            # Créer une alerte si pas encore créée
            existing_alert = self.db.query(Alert).filter(
                and_(
                    Alert.related_id == invoice.id,
                    Alert.type == 'unpaid_invoice',
                    Alert.status == 'active'
                )
            ).first()

            if not existing_alert:
                alert = Alert(
                    type='unpaid_invoice',
                    message=f"Facture {invoice.invoice_number} en retard de paiement de {remaining_amount}€",
                    related_id=invoice.id,
                    related_type='invoice',
                    status='active'
                )
                self.db.add(alert)

        self.db.commit()
        return result

    async def track_unpaid_checks(self) -> List[Dict]:
        """Suivre les chèques impayés"""
        unpaid_checks = self.db.query(Check).filter(Check.status == 'unpaid').all()

        result = []
        for check in unpaid_checks:
            transaction = self.db.query(PaymentTransaction).filter(
                PaymentTransaction.id == check.transaction_id
            ).first()

            if transaction:
                invoice = self.db.query(Invoice).filter(
                    Invoice.id == transaction.invoice_id
                ).first()

                client = self.db.query(Client).filter(
                    Client.id == transaction.client_id
                ).first()

                result.append({
                    "check_number": check.check_number,
                    "amount": float(check.amount),
                    "bank_name": check.bank_name,
                    "client_name": client.name if client else "Unknown",
                    "invoice_number": invoice.invoice_number if invoice else None,
                    "check_date": check.check_date,
                    "days_since_unpaid": (datetime.now() - check.check_date).days
                })

        return result

    async def generate_unpaid_report(self, client_id: Optional[str] = None) -> Dict:
        """Générer un rapport détaillé des impayés"""
        # Requête de base pour les factures impayées
        invoice_query = self.db.query(Invoice).filter(Invoice.status != 'paid')
        check_query = self.db.query(Check).filter(Check.status == 'unpaid')

        if client_id:
            invoice_query = invoice_query.filter(Invoice.client_id == client_id)
            check_query = check_query.join(PaymentTransaction).filter(
                PaymentTransaction.client_id == client_id
            )

        unpaid_invoices = invoice_query.all()
        unpaid_checks = check_query.all()

        total_unpaid_amount = sum(float(invoice.total) for invoice in unpaid_invoices)
        total_unpaid_checks_amount = sum(float(check.amount) for check in unpaid_checks)

        return {
            "summary": {
                "total_unpaid_invoices": len(unpaid_invoices),
                "total_unpaid_amount": total_unpaid_amount,
                "total_unpaid_checks": len(unpaid_checks),
                "total_unpaid_checks_amount": total_unpaid_checks_amount,
                "total_exposure": total_unpaid_amount + total_unpaid_checks_amount
            },
            "unpaid_invoices": [
                {
                    "invoice_number": inv.invoice_number,
                    "amount": float(inv.total),
                    "due_date": inv.due_date,
                    "days_overdue": (datetime.now() - inv.due_date).days
                } for inv in unpaid_invoices
            ],
            "unpaid_checks": [
                {
                    "check_number": chk.check_number,
                    "amount": float(chk.amount),
                    "bank_name": chk.bank_name,
                    "check_date": chk.check_date
                } for chk in unpaid_checks
            ]
        }

    async def send_payment_reminder(self, invoice_id: str) -> Dict:
        """Envoyer un rappel de paiement"""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Facture non trouvée")

        client = self.db.query(Client).filter(Client.id == invoice.client_id).first()
        if not client:
            raise ValueError("Client non trouvé")

        # Créer une alerte de rappel
        alert = Alert(
            type='payment_reminder',
            message=f"Rappel de paiement envoyé pour la facture {invoice.invoice_number}",
            related_id=invoice.id,
            related_type='invoice',
            status='active'
        )
        self.db.add(alert)
        self.db.commit()

        return {
            "invoice_number": invoice.invoice_number,
            "client_name": client.name,
            "amount": float(invoice.total),
            "due_date": invoice.due_date,
            "reminder_sent": datetime.now()
        }

    async def get_client_payment_history(self, client_id: str) -> Dict:
        """Obtenir l'historique des paiements d'un client"""
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise ValueError("Client non trouvé")

        invoices = self.db.query(Invoice).filter(Invoice.client_id == client_id).all()
        transactions = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.client_id == client_id
        ).all()

        total_invoiced = sum(float(inv.total) for inv in invoices)
        total_paid = sum(
            float(trans.amount)
            for trans in transactions
            if trans.status == 'completed'
        )

        return {
            "client_info": {
                "name": client.name,
                "status": client.status
            },
            "payment_summary": {
                "total_invoiced": total_invoiced,
                "total_paid": total_paid,
                "payment_ratio": (total_paid / total_invoiced * 100) if total_invoiced > 0 else 0
            },
            "unpaid_invoices": [
                {
                    "invoice_number": inv.invoice_number,
                    "amount": float(inv.total),
                    "due_date": inv.due_date,
                    "days_overdue": (datetime.now() - inv.due_date).days
                } for inv in invoices if inv.status != 'paid'
            ],
            "payment_history": [
                {
                    "date": trans.transaction_date,
                    "amount": float(trans.amount),
                    "method": trans.payment_method,
                    "status": trans.status
                } for trans in transactions
            ]
        }
