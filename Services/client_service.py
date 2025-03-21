from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional, Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from Models.Client import Client
from Models.Invoice import Invoice
from Models.PaymentTransaction import PaymentTransaction
from Models.Alert import Alert
import logging
import uuid
from decimal import Decimal

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClientCategory:
    STANDARD = "standard"
    KEY_ACCOUNT = "key_account"
    INACTIVE = "inactive"

class ClientService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_client(self, client_data: Dict) -> Client:
        """Create a new client"""
        client = Client(
            id=str(uuid.uuid4()),
            name=client_data['name'],
            email=client_data['email'],
            phone=client_data['phone'],
            address=client_data['address'],
            status=client_data.get('status', ClientCategory.STANDARD),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self.db.add(client)
        await self.db.commit()  # Await the commit
        await self.db.refresh(client)  # Refresh to get the updated instance
        logger.info(f"Client created: {client.id}")
        return client
    
    async def get_client_by_details(self, name: str, email: str) -> Optional[Client]:
        """Check if a client exists by name and email."""
        result = await self.db.execute(
            select(Client).where(Client.name == name, Client.email == email)
        )
        return result.scalar_one_or_none()


    async def update_client(self, client_id: str, client_data: Dict) -> Optional[Client]:
        """Update client information"""
        client = await self.get_client_by_id(client_id)
        if not client:
            logger.warning(f"Client with ID {client_id} not found for update.")
            return None

        for key, value in client_data.items():
            if hasattr(client, key):
                setattr(client, key, value)

        client.updated_at = datetime.now()
        await self.db.commit()  # Await the commit
        logger.info(f"Client updated: {client.id}")
        return client

    async def get_client_status(self) -> List[Dict]:
        """Get the status of all clients with metrics"""
        result = await self.db.execute(select(Client))
        clients = result.scalars().all()  # Get the list of clients
        metrics_list = []

        for client in clients:
            metrics = await self.calculate_client_metrics(client.id)
            metrics_list.append({
                "id": client.id,
                "name": client.name,
                "status": client.status,
                "revenue": client.revenue,
                "metrics": metrics
            })

        logger.info("Retrieved client status for all clients.")
        return metrics_list

    async def get_client_by_id(self, client_id: str) -> Optional[Client]:
            result = await self.db.execute(select(Client).where(Client.id == client_id))
            client = result.scalar_one_or_none()
            if not client:
                logger.warning(f"Client {client_id} not found")
            return client
        

    async def update_client_status(self, client_id: str, new_status: str) -> bool:
        """Update a client's status with notification"""
        client = await self.get_client_by_id(client_id)
        if not client:
            logger.warning(f"Client with ID {client_id} not found for status update.")
            return False

        old_status = client.status
        client.status = new_status
        client.updated_at = datetime.now()

        # Create an alert if the status changes to key account
        if new_status == ClientCategory.KEY_ACCOUNT and old_status != ClientCategory.KEY_ACCOUNT:
            alert = Alert(
                type="client_status_change",
                message=f"Client {client.name} is now a key account",
                related_id=client.id,
                related_type="client",
                status="active"
            )
            self.db.add(alert)

        await self.db.commit()  # Await the commit
        logger.info(f"Client status updated: {client.id} to {new_status}")
        return True

    async def get_semiannual_revenue(self, client_id: str) -> Dict:
        """Calculate detailed semi-annual revenue"""
        six_months_ago = datetime.now() - timedelta(days=180)

        # Total revenue
        total_revenue = await self.db.execute(
            select(func.sum(Invoice.total)).where(
                Invoice.client_id == client_id,
                Invoice.date >= six_months_ago
            )
        )
        total_revenue = total_revenue.scalar() or Decimal(0.0)  # Ensure it's a Decimal

        # Monthly breakdown
        monthly_revenue = await self.db.execute(
            select(func.strftime('%Y-%m', Invoice.date).label('month'),
                   func.sum(Invoice.total).label('revenue')).where(
                Invoice.client_id == client_id,
                Invoice.date >= six_months_ago
            ).group_by(func.strftime('%Y-%m', Invoice.date))
        )

        monthly_revenue_data = monthly_revenue.all()

        logger.info(f"Semi-annual revenue calculated for client ID {client_id}.")
        return {
            "total_revenue": float(total_revenue),  # Convert to float for consistency
            "monthly_breakdown": [
                {
                    "month": month,
                    "revenue": float(revenue)  # Convert to float for consistency
                } for month, revenue in monthly_revenue_data
            ]
        }

    async def get_key_accounts(self) -> List[Dict]:
        """Get detailed list of key accounts"""
        try:
            # Correction de la requête SQL
            stmt = select(Client).where(Client.status == ClientCategory.KEY_ACCOUNT)
            result = await self.db.execute(stmt)
            key_accounts = result.scalars().all()

            if not key_accounts:
                return []

            metrics_list = []
            for client in key_accounts:
                try:
                    # Gestion des erreurs pour chaque client
                    metrics = await self.calculate_client_metrics(client.id)
                    metrics_list.append({
                        "client_info": {
                            "id": client.id,
                            "name": client.name,
                            "email": client.email,
                            "phone": client.phone
                        },
                        "metrics": metrics
                    })
                except Exception as e:
                    logger.error(f"Erreur sur le client {client.id} : {str(e)}")
                    await self.db.rollback()

            return metrics_list

        except SQLAlchemyError as e:
            logger.error(f"Erreur SQL : {str(e)}")
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Database error")

        except Exception as e:
            logger.error(f"Erreur inattendue : {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def create_client_dashboard(self, client_id: str) -> Dict:
        """Generate a complete client dashboard"""
        client = await self.get_client_by_id(client_id)
        if not client:
            logger.error(f"Client with ID {client_id} not found.")
            return None  

        # Base metrics
        metrics = await self.calculate_client_metrics(client_id)

        # Payment history
        payment_history = await self.get_payment_history(client_id)

        # Delay analysis
        delay_analysis = await self.analyze_payment_delays(client_id)

        logger.info(f"Client dashboard created for client ID {client_id}.")
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
        """Calculate detailed metrics for a client"""
        total_invoices = await self.db.execute(
            select(func.count()).where(Invoice.client_id == client_id)
        )
        total_invoices = total_invoices.scalar() or 0

        paid_invoices = await self.db.execute(
            select(func.count()).where(
                Invoice.client_id == client_id,
                Invoice.status == 'paid'
            )
        )
        paid_invoices = paid_invoices.scalar() or 0

        # Amounts
        total_amount = await self.db.execute(
            select(func.sum(Invoice.total)).where(Invoice.client_id == client_id)
        )
        total_amount = total_amount.scalar() or Decimal(0.0)  # Ensure it's a Decimal

        paid_amount = await self.db.execute(
            select(func.sum(PaymentTransaction.amount)).where(
                PaymentTransaction.client_id == client_id,
                PaymentTransaction.status == 'completed'
            )
        )
        paid_amount = paid_amount.scalar() or Decimal(0.0)  # Ensure it's a Decimal

        logger.info(f"Metrics calculated for client ID {client_id}.")
        return {
            "invoices": {
                "total": total_invoices,
                "paid": paid_invoices,
                "payment_ratio": paid_invoices / total_invoices if total_invoices > 0 else 0
            },
            "amounts": {
                "total": float(total_amount),  # Convert to float for consistency
                "paid": float(paid_amount),  # Convert to float for consistency
                "remaining": float(total_amount - paid_amount)  # Ensure both are floats
            }
        }

    async def get_payment_history(self, client_id: str) -> List[Dict]:
        """Get detailed payment history"""
        result = await self.db.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.client_id == client_id
            ).order_by(PaymentTransaction.created_at.desc())
        )
        transactions = result.scalars().all()

        logger.info(f"Payment history retrieved for client ID {client_id}.")
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
        """Analyze payment delays"""
        invoices = await self.db.execute(
            select(Invoice).where(Invoice.client_id == client_id)
        )
        invoices = invoices.scalars().all()

        total_delay_days = 0
        delayed_invoices = 0

        for invoice in invoices:
            if invoice.status == 'paid':
                payment = await self.db.execute(
                    select(PaymentTransaction).where(
                        PaymentTransaction.invoice_id == invoice.id,
                        PaymentTransaction.status == 'completed'
                    )
                )
                payment = payment.scalar_one_or_none()

                if payment and invoice.due_date:
                    delay = (payment.transaction_date - invoice.due_date).days
                    if delay > 0:
                        total_delay_days += delay
                        delayed_invoices += 1

        current_overdue_invoices = await self.db.execute(
            select(func.count()).where(
                Invoice.client_id == client_id,
                Invoice.status != 'paid',
                Invoice.due_date < datetime.now()
            )
        ).scalar()

        logger.info(f"Payment delays analyzed for client ID {client_id}.")
        return {
            "total_delayed_invoices": delayed_invoices,
            "average_delay_days": total_delay_days / delayed_invoices if delayed_invoices > 0 else 0,
            "current_overdue_invoices": current_overdue_invoices
        }
    

    async def delete_client(self, client_id: str) -> bool:

        """Delete a client by ID"""
        client = await self.get_client_by_id(client_id)
        if not client:
            return False

        self.db.delete(client)
        await self.db.commit()

        return True


    async def search_clients(self, name: Optional[str], email: Optional[str], status: Optional[ClientCategory]) -> List[Client]:

        """Search for clients based on name, email, or status"""
        query = select(Client)
        if name:
            query = query.where(Client.name.ilike(f"%{name}%"))
        if email:
            query = query.where(Client.email.ilike(f"%{email}%"))
        if status:
            query = query.where(Client.status == status)

        result = await self.db.execute(query)

        return result.scalars().all()