from fastapi import APIRouter, HTTPException, Body, Path, Query, Depends
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, condecimal
from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy.orm import Session

from Services.PaymentService import PaymentService
from database import get_db_connection

router = APIRouter(tags=["payments"])


# Enums for validation
class PaymentMethod(str, Enum):
    CHECK = "check"
    CASH = "cash"
    TRANSFER = "transfer"
    CARD = "card"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


# Pydantic models
class PaymentCreate(BaseModel):
    invoice_id: str = Field(..., description="ID of the invoice to pay")
    payment_method: PaymentMethod = Field(..., description="Method of payment")
    amount: condecimal(gt=Decimal('0')) = Field(..., description="Payment amount")

    model_config = {
        "json_schema_extra": {
            "example": {
                "invoice_id": "123e4567-e89b-12d3-a456-426614174000",
                "payment_method": "check",
                "amount": 1000.00
            }
        }
    }


class CheckReplacementInfo(BaseModel):
    amount: condecimal(gt=Decimal('0')) = Field(..., description="Amount for the new check")
    bank_name: str = Field(..., description="Name of the bank")
    bank_branch: str = Field(..., description="Bank branch")
    bank_account: str = Field(..., description="Bank account number")
    swift_code: str = Field(..., description="SWIFT code")

    model_config = {
        "json_schema_extra": {
            "example": {
                "amount": 1000.00,
                "bank_name": "Example Bank",
                "bank_branch": "Main Branch",
                "bank_account": "123456789",
                "swift_code": "EXAMPLEBK"
            }
        }
    }


def get_payment_service(db: Session = Depends(get_db_connection)) -> PaymentService:
    return PaymentService(db)


@router.post("/payments/process", response_model=Dict)
async def process_payment(
        payment: PaymentCreate,
        service: PaymentService = Depends(get_payment_service)
):
    """
    Process a new payment.

    - Handles different payment methods
    - Automatically divides large checks
    - Updates invoice status
    - Returns transaction details
    """
    try:
        result = await service.process_payment(
            invoice_id=payment.invoice_id,
            payment_method=payment.payment_method.value,
            amount=float(payment.amount)
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process payment: {str(e)}"
        )


@router.post("/payments/checks/{check_id}/replace", response_model=Dict)
async def replace_check(
        check_id: str = Path(..., description="ID of the check to replace"),
        replacement_info: CheckReplacementInfo = Body(...),
        service: PaymentService = Depends(get_payment_service)
):
    """
    Replace a bounced check with a new one.

    - Creates new check with provided details
    - Marks old check as replaced
    - Creates alert for check replacement
    - Returns replacement details
    """
    try:
        result = await service.handle_check_replacement(
            old_check_id=check_id,
            new_check_info=replacement_info.dict()
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to replace check: {str(e)}"
        )


@router.get("/payments/status/{invoice_id}", response_model=Dict)
async def get_payment_status(
        invoice_id: str = Path(..., description="ID of the invoice to check"),
        service: PaymentService = Depends(get_payment_service)
):
    """
    Get payment status for an invoice.

    - Returns payment status and details
    - Includes transaction history
    - Shows remaining amount
    """
    try:
        result = await service.get_payment_status(invoice_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get payment status: {str(e)}"
        )


@router.get("/payments/transactions", response_model=List[Dict])
async def list_transactions(
        client_id: Optional[str] = Query(None, description="Filter by client ID"),
        payment_method: Optional[PaymentMethod] = Query(None, description="Filter by payment method"),
        status: Optional[PaymentStatus] = Query(None, description="Filter by status"),
        from_date: Optional[datetime] = Query(None, description="Filter from date"),
        to_date: Optional[datetime] = Query(None, description="Filter to date"),
        service: PaymentService = Depends(get_payment_service)
):
    """
    List payment transactions with filtering options.

    - Can filter by client, payment method, status, and date range
    - Returns list of matching transactions
    """
    try:
        transactions = await service.list_transactions(
            client_id=client_id,
            payment_method=payment_method.value if payment_method else None,
            status=status.value if status else None,
            from_date=from_date,
            to_date=to_date
        )
        return transactions
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list transactions: {str(e)}"
        )


@router.get("/payments/checks/pending", response_model=List[Dict])
async def list_pending_checks(
        client_id: Optional[str] = Query(None, description="Filter by client ID"),
        from_date: Optional[datetime] = Query(None, description="Filter from date"),
        to_date: Optional[datetime] = Query(None, description="Filter to date"),
        service: PaymentService = Depends(get_payment_service)
):
    """
    List pending checks.

    - Can filter by client and date range
    - Returns list of pending checks with client information
    """
    try:
        checks = await service.list_pending_checks(
            client_id=client_id,
            from_date=from_date,
            to_date=to_date
        )
        return checks
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list pending checks: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(router, host="0.0.0.0", port=8000)
