from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from Services.unpaid_tracking_service import UnpaidTrackingService
from database import get_db_connection

router = APIRouter(
    prefix="/unpaid",
    tags=["unpaid"]
)

@router.get("/invoices/")
async def get_unpaid_invoices(
    days_overdue: int = Query(30, description="Nombre de jours de retard minimum"),
    db: Session = Depends(get_db_connection)
):
    """Récupérer la liste des factures impayées"""
    try:
        service = UnpaidTrackingService(db)
        return await service.track_unpaid_invoices(days_overdue)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/checks/")
async def get_unpaid_checks(
    db: Session = Depends(get_db_connection)
):
    """Récupérer la liste des chèques impayés"""
    try:
        service = UnpaidTrackingService(db)
        return await service.track_unpaid_checks()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/report/")
async def generate_unpaid_report(
    client_id: Optional[str] = Query(None, description="ID du client (optionnel)"),
    db: Session = Depends(get_db_connection)
):
    """Générer un rapport détaillé des impayés"""
    try:
        service = UnpaidTrackingService(db)
        return await service.generate_unpaid_report(client_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reminder/{invoice_id}")
async def send_payment_reminder(
    invoice_id: str,
    db: Session = Depends(get_db_connection)
):
    """Envoyer un rappel de paiement pour une facture"""
    try:
        service = UnpaidTrackingService(db)
        return await service.send_payment_reminder(invoice_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{client_id}")
async def get_client_payment_history(
    client_id: str,
    db: Session = Depends(get_db_connection)
):
    """Obtenir l'historique des paiements d'un client"""
    try:
        service = UnpaidTrackingService(db)
        return await service.get_client_payment_history(client_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
