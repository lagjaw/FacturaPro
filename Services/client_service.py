from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from Models.Client import Client
from Models.Invoice import Invoice
from Models.PaymentTransaction import PaymentTransaction
from Models.Alert import Alert


class ClientCategory:
    STANDARD = "standard"
    KEY_ACCOUNT = "key_account"
    INACTIVE = "inactive"


class ClientService:
    def __init__(self, db: Session):
        self.db = db

    async def create_client(self, client_data: Dict) -> Client:
        """Créer un nouveau client"""
        client = Client(
            name=client_data['name'],
            email=client_data['email'],
            phone=client_data['phone'],
            address=client_data['address'],
            status=client_data.get('status', ClientCategory.STANDARD),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.db.add(client)
        self.db.commit()
        return client

    async def update_client(self, client_id: str, client_data: Dict) -> Optional[Client]:
        """Mettre à jour les informations d'un client"""
        client = await self.get_client_by_id(client_id)
        if not client:
            return None

        for key, value in client_data.items():
            if hasattr(client, key):
                setattr(client, key, value)

        client.updated_at = datetime.now()
        self.db.commit()
        return client

    async def get_client_status(self) -> List[Dict]:
        """Obtenir le statut de tous les clients avec métriques"""
        clients = self.db.query(Client).all()
        result = []

        for client in clients:
            metrics = await self.calculate_client_metrics(client.id)
            result.append({
                "id": client.id,
                "name": client.name,
                "status": client.status,
                "revenue": client.revenue,
                "metrics": metrics
            })

        return result

    async def get_client_by_id(self, client_id: str) -> Optional[Client]:
        """Obtenir les informations détaillées d'un client"""
        return self.db.query(Client).filter(Client.id == client_id).first()

    async def update_client_status(self, client_id: str, new_status: str) -> bool:
        """Mettre à jour le statut d'un client avec notification"""
        client = await self.get_client_by_id(client_id)
        if not client:
            return False

        old_status = client.status
        client.status = new_status
        client.updated_at = datetime.now()

        # Créer une alerte si passage en grand compte
        if new_status == ClientCategory.KEY_ACCOUNT and old_status != ClientCategory.KEY_ACCOUNT:
            alert = Alert(
                type="client_status_change",
                message=f"Client {client.name} est maintenant un grand compte",
                related_id=client.id,
                related_type="client",
                status="active"
            )
            self.db.add(alert)

        self.db.commit()
        return True

    async def get_semiannual_revenue(self, client_id: str) -> Dict:
        """Calculer le chiffre d'affaires semestriel détaillé"""
        six_months_ago = datetime.now() - timedelta(days=180)

        # Chiffre d'affaires total
        total_revenue = self.db.query(func.sum(Invoice.total)).filter(
            Invoice.client_id == client_id,
            Invoice.date >= six_months_ago
        ).scalar() or 0.0

        # Répartition mensuelle
        monthly_revenue = self.db.query(
            func.date_trunc('month', Invoice.date).label('month'),
            func.sum(Invoice.total).label('revenue')
        ).filter(
            Invoice.client_id == client_id,
            Invoice.date >= six_months_ago
        ).group_by('month').all()

        return {
            "total_revenue": total_revenue,
            "monthly_breakdown": [
                {
                    "month": month.strftime("%Y-%m"),
                    "revenue": float(revenue)
                } for month, revenue in monthly_revenue
            ]
        }

    async def get_key_accounts(self) -> List[Dict]:
        """Obtenir la liste détaillée des grands comptes"""
        key_accounts = self.db.query(Client).filter(
            Client.status == ClientCategory.KEY_ACCOUNT
        ).all()

        result = []
        for client in key_accounts:
            metrics = await self.calculate_client_metrics(client.id)
            result.append({
                "client_info": {
                    "id": client.id,
                    "name": client.name,
                    "email": client.email,
                    "phone": client.phone
                },
                "metrics": metrics
            })

        return result

    async def create_client_dashboard(self, client_id: str) -> Dict:
        """Générer un tableau de bord client complet"""
        client = await self.get_client_by_id(client_id)
        if not client:
            return None

        # Métriques de base
        metrics = await self.calculate_client_metrics(client_id)

        # Historique des paiements
        payment_history = await self.get_payment_history(client_id)

        # Analyse des retards
        delay_analysis = await self.analyze_payment_delays(client_id)

        return {
            "client_info": {
                "id": client.id,
                "name": client.name,
                "status": client.status,
                "revenue": client.revenue
            },
            "metrics": metrics,
            "payment_history": payment_history,
            "delay_analysis": delay_analysis
        }

    async def calculate_client_metrics(self, client_id: str) -> Dict:
        """Calculer les métriques détaillées d'un client"""
        # Factures
        total_invoices = self.db.query(Invoice).filter(
            Invoice.client_id == client_id
        ).count()

        paid_invoices = self.db.query(Invoice).filter(
            Invoice.client_id == client_id,
            Invoice.status == 'paid'
        ).count()

        # Montants
        total_amount = self.db.query(func.sum(Invoice.total)).filter(
            Invoice.client_id == client_id
        ).scalar() or 0.0

        paid_amount = self.db.query(func.sum(PaymentTransaction.amount)).filter(
            PaymentTransaction.client_id == client_id,
            PaymentTransaction.status == 'completed'
        ).scalar() or 0.0

        return {
            "invoices": {
                "total": total_invoices,
                "paid": paid_invoices,
                "payment_ratio": paid_invoices / total_invoices if total_invoices > 0 else 0
            },
            "amounts": {
                "total": float(total_amount),
                "paid": float(paid_amount),
                "remaining": float(total_amount - paid_amount)
            }
        }

    async def get_payment_history(self, client_id: str) -> List[Dict]:
        """Obtenir l'historique détaillé des paiements"""
        transactions = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.client_id == client_id
        ).order_by(PaymentTransaction.created_at.desc()).all()

        return [
            {
                "id": t.id,
                "amount": float(t.amount),
                "method": t.payment_method,
                "status": t.status,
                "date": t.created_at,
                "invoice_id": t.invoice_id
            } for t in transactions
        ]

    async def analyze_payment_delays(self, client_id: str) -> Dict:
        """Analyser les retards de paiement"""
        invoices = self.db.query(Invoice).filter(
            Invoice.client_id == client_id
        ).all()

        total_delay_days = 0
        delayed_invoices = 0

        for invoice in invoices:
            if invoice.status == 'paid':
                payment = self.db.query(PaymentTransaction).filter(
                    PaymentTransaction.invoice_id == invoice.id,
                    PaymentTransaction.status == 'completed'
                ).first()

                if payment and invoice.due_date:
                    delay = (payment.transaction_date - invoice.due_date).days
                    if delay > 0:
                        total_delay_days += delay
                        delayed_invoices += 1

        return {
            "total_delayed_invoices": delayed_invoices,
            "average_delay_days": total_delay_days / delayed_invoices if delayed_invoices > 0 else 0,
            "current_overdue_invoices": self.db.query(Invoice).filter(
                Invoice.client_id == client_id,
                Invoice.status != 'paid',
                Invoice.due_date < datetime.now()
            ).count()
        }
