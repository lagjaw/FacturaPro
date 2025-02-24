from fastapi import APIRouter, HTTPException, Path, Query, Depends, Body
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from Services.transaction_alert_service import TransactionAlertService
from database import get_db_connection

router = APIRouter(tags=["transaction-alerts"])


# Pydantic models
class AlertStatusUpdate(BaseModel):
    status: str = Field(..., description="New status for the alert")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "Resolved"
            }
        }
    }


def get_alert_service(db: Session = Depends(get_db_connection)) -> TransactionAlertService:
    return TransactionAlertService(db)


@router.post("/transactions/{transaction_id}/alerts", response_model=Dict)
async def create_alert(
        transaction_id: str = Path(..., description="ID of the transaction to check"),
        service: TransactionAlertService = Depends(get_alert_service)
):
    """
    Create an alert for a specific transaction if it's overdue or failed.

    - Checks transaction status and due date
    - Creates alert if conditions are met
    - Returns alert details if created
    """
    try:
        alert = await service.create_transaction_alert(transaction_id)
        if alert:
            return alert
        return {"message": "No alert needed for this transaction"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create alert: {str(e)}"
        )


@router.get("/transactions/alerts/check-overdue", response_model=List[Dict])
async def check_overdue_transactions(
        service: TransactionAlertService = Depends(get_alert_service)
):
    """
    Check all transactions for overdue status and create alerts.

    - Checks all transactions
    - Creates alerts for overdue transactions
    - Returns list of created alerts
    """
    try:
        alerts = await service.check_overdue_transactions()
        return alerts
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check overdue transactions: {str(e)}"
        )


@router.get("/transactions/alerts", response_model=List[Dict])
async def get_alerts(
        transaction_id: Optional[str] = Query(None, description="Filter by transaction ID"),
        status: Optional[str] = Query(None, description="Filter by alert status"),
        service: TransactionAlertService = Depends(get_alert_service)
):
    """
    Get transaction alerts with optional filtering.

    - Can filter by transaction ID
    - Can filter by alert status
    - Returns list of matching alerts
    """
    try:
        alerts = await service.get_transaction_alerts(
            transaction_id=transaction_id,
            status=status
        )
        return alerts
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get alerts: {str(e)}"
        )


@router.put("/transactions/alerts/{alert_id}", response_model=Dict)
async def update_alert_status(
        alert_id: str = Path(..., description="ID of the alert to update"),
        status_update: AlertStatusUpdate = Body(...),
        service: TransactionAlertService = Depends(get_alert_service)
):
    """
    Update the status of an alert.

    - Updates alert status
    - Records update timestamp
    - Returns updated alert details
    """
    try:
        alert = await service.update_alert_status(
            alert_id=alert_id,
            status=status_update.status
        )
        return alert
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update alert status: {str(e)}"
        )


@router.get("/transactions/alerts/summary", response_model=Dict)
async def get_alerts_summary(
        service: TransactionAlertService = Depends(get_alert_service)
):
    """
    Get a summary of transaction alerts.

    - Count of alerts by status
    - Count of alerts by transaction
    - Recent alert history
    """
    # Note: This would require adding a new method to TransactionAlertService
    raise HTTPException(
        status_code=501,
        detail="This endpoint is not yet implemented"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(router, host="0.0.0.0", port=8000)
