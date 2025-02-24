from fastapi import APIRouter, HTTPException, Path, Query, Depends, Body
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, condecimal
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session


from Services.transaction_service import TransactionService
from database import get_db_connection

router = APIRouter(tags=["transactions"])


# Pydantic models
class TransactionCreate(BaseModel):
    client_id: str = Field(..., description="ID of the client")
    invoice_id: str = Field(..., description="ID of the invoice")
    amount: condecimal(gt=Decimal('0')) = Field(..., description="Transaction amount")
    payment_method: str = Field(..., description="Method of payment")
    due_date: datetime = Field(..., description="Due date for the transaction")
    transaction_date: Optional[datetime] = Field(None, description="Date of the transaction")
    status: str = Field("Pending", description="Transaction status")

    model_config = {
        "json_schema_extra": {
            "example": {
                "client_id": "123e4567-e89b-12d3-a456-426614174000",
                "invoice_id": "123e4567-e89b-12d3-a456-426614174001",
                "amount": 1000.00,
                "payment_method": "check",
                "due_date": "2024-12-31T23:59:59",
                "transaction_date": "2024-01-01T12:00:00",
                "status": "Pending"
            }
        }
    }


class TransactionStatusUpdate(BaseModel):
    status: str = Field(..., description="New status for the transaction")
    paid_amount: Optional[condecimal(gt=Decimal('0'))] = Field(None, description="Amount paid")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "Completed",
                "paid_amount": 1000.00
            }
        }
    }


def get_transaction_service(db: Session = Depends(get_db_connection)) -> TransactionService:
    return TransactionService(db)


@router.post("/transactions", response_model=Dict)
async def create_transaction(
        transaction: TransactionCreate,
        service: TransactionService = Depends(get_transaction_service)
):
    """
    Create a new transaction.

    - Creates transaction with specified details
    - Calculates remaining amount
    - Returns created transaction details
    """
    try:
        result = await service.create_transaction(
            client_id=transaction.client_id,
            invoice_id=transaction.invoice_id,
            amount=float(transaction.amount),
            payment_method=transaction.payment_method,
            due_date=transaction.due_date,
            transaction_date=transaction.transaction_date,
            status=transaction.status
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create transaction: {str(e)}"
        )


@router.get("/transactions/{transaction_id}", response_model=Dict)
async def get_transaction(
        transaction_id: str = Path(..., description="ID of the transaction to retrieve"),
        service: TransactionService = Depends(get_transaction_service)
):
    """
    Get transaction details.

    - Returns complete transaction information
    - Includes payment and status details
    """
    try:
        result = await service.get_transaction(transaction_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get transaction: {str(e)}"
        )


@router.put("/transactions/{transaction_id}/status", response_model=Dict)
async def update_transaction_status(
        transaction_id: str = Path(..., description="ID of the transaction to update"),
        update: TransactionStatusUpdate = Body(...),
        service: TransactionService = Depends(get_transaction_service)
):
    """
    Update transaction status.

    - Updates status and optionally paid amount
    - Recalculates remaining amount if paid amount provided
    - Returns updated transaction details
    """
    try:
        result = await service.update_transaction_status(
            transaction_id=transaction_id,
            status=update.status,
            paid_amount=float(update.paid_amount) if update.paid_amount else None
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update transaction status: {str(e)}"
        )


@router.get("/transactions/client/{client_id}", response_model=List[Dict])
async def get_client_transactions(
        client_id: str = Path(..., description="ID of the client"),
        status: Optional[str] = Query(None, description="Filter by status"),
        payment_method: Optional[str] = Query(None, description="Filter by payment method"),
        from_date: Optional[datetime] = Query(None, description="Filter from date"),
        to_date: Optional[datetime] = Query(None, description="Filter to date"),
        service: TransactionService = Depends(get_transaction_service)
):
    """
    Get all transactions for a client.

    - Can filter by status and payment method
    - Can filter by date range
    - Returns list of matching transactions
    """
    try:
        transactions = await service.get_client_transactions(
            client_id=client_id,
            status=status,
            payment_method=payment_method,
            from_date=from_date,
            to_date=to_date
        )
        return transactions
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get client transactions: {str(e)}"
        )


@router.get("/transactions/invoice/{invoice_id}", response_model=List[Dict])
async def get_invoice_transactions(
        invoice_id: str = Path(..., description="ID of the invoice"),
        service: TransactionService = Depends(get_transaction_service)
):
    """
    Get all transactions for an invoice.

    - Returns all payments for the specified invoice
    - Includes payment details and status
    """
    try:
        transactions = await service.get_invoice_transactions(invoice_id)
        return transactions
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get invoice transactions: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(router, host="0.0.0.0", port=8000)
