from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session

from Models.Alert import Alert
from Models.PaymentTransaction import PaymentTransaction


class TransactionAlertService:
    def __init__(self, db: Session):
        self.db = db

    async def create_transaction_alert(self, transaction_id: str) -> Optional[Dict]:
        """Create an alert for overdue or failed transactions"""
        transaction = self.db.query(PaymentTransaction).filter_by(id=transaction_id).first()

        if not transaction:
            raise ValueError(f"Transaction with id {transaction_id} not found.")

        if transaction.status != "Completed" and transaction.due_date < datetime.utcnow():
            alert = Alert(
                type="Transaction Alert",
                message=f"Transaction {transaction.id} is overdue or failed.",
                related_id=transaction.id,
                related_type="Transaction",
                status="Active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            self.db.add(alert)
            self.db.commit()

            return {
                "id": alert.id,
                "type": alert.type,
                "message": alert.message,
                "related_id": alert.related_id,
                "related_type": alert.related_type,
                "status": alert.status,
                "created_at": alert.created_at,
                "transaction_details": {
                    "id": transaction.id,
                    "amount": float(transaction.amount),
                    "due_date": transaction.due_date,
                    "status": transaction.status
                }
            }

        return None

    async def check_overdue_transactions(self) -> List[Dict]:
        """Check all transactions for overdue status and create alerts"""
        overdue_transactions = (
            self.db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.status != "Completed",
                PaymentTransaction.due_date < datetime.utcnow()
            )
            .all()
        )

        alerts = []
        for transaction in overdue_transactions:
            alert = await self.create_transaction_alert(transaction.id)
            if alert:
                alerts.append(alert)

        return alerts

    async def get_transaction_alerts(
            self,
            transaction_id: Optional[str] = None,
            status: Optional[str] = None
    ) -> List[Dict]:
        """Get alerts for a specific transaction or all active alerts"""
        query = self.db.query(Alert).filter(Alert.related_type == "Transaction")

        if transaction_id:
            query = query.filter(Alert.related_id == transaction_id)
        if status:
            query = query.filter(Alert.status == status)

        alerts = query.all()

        return [{
            "id": alert.id,
            "type": alert.type,
            "message": alert.message,
            "related_id": alert.related_id,
            "status": alert.status,
            "created_at": alert.created_at,
            "updated_at": alert.updated_at
        } for alert in alerts]

    async def update_alert_status(self, alert_id: str, status: str) -> Dict:
        """Update the status of an alert"""
        alert = self.db.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            raise ValueError(f"Alert with id {alert_id} not found.")

        alert.status = status
        alert.updated_at = datetime.utcnow()
        self.db.commit()

        return {
            "id": alert.id,
            "type": alert.type,
            "message": alert.message,
            "related_id": alert.related_id,
            "status": alert.status,
            "updated_at": alert.updated_at
        }
