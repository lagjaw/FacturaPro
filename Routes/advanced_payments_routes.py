from fastapi import APIRouter, HTTPException, Body, Path, Query, Depends
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from Services.advanced_payment_service import AdvancedPaymentService
from database import get_db_session
import logging
import sqlite3

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router with prefix and tags matching main.py configuration
router = APIRouter()
advanced_payments_router = router  # Export the router with the name used in main.py

# Pydantic models
class CheckDivisionRequest(BaseModel):
    amounts: List[float] = Field(..., description="List of amounts for the division")
    division_date: datetime = Field(..., description="Date of the division")
    status: str = Field("pending", description="Status of the division")

    @property
    def total_amount(self) -> float:
        return sum(self.amounts)

    class Config:
        json_schema_extra = {
            "example": {
                "amounts": [300, 200],
                "division_date": "2025-02-01",
                "status": "pending"
            }
        }

class NewCheckInfo(BaseModel):
    check_number: str = Field(..., description="New check number")
    amount: float = Field(..., gt=0, description="Check amount")
    bank_name: str = Field(..., description="Bank name")
    bank_branch: str = Field(..., description="Bank branch")
    bank_account: str = Field(..., description="Bank account number")
    swift_code: str = Field(..., description="SWIFT code")

    class Config:
        json_schema_extra = {
            "example": {
                "check_number": "12345678",
                "amount": 2000.00,
                "bank_name": "Example Bank",
                "bank_branch": "Main Branch",
                "bank_account": "1234567890",
                "swift_code": "EXAMPLEBK"
            }
        }

class CheckPaymentInfo(BaseModel):
    check_number: str = Field(..., description="Check number")
    amount: float = Field(..., gt=0, description="Check amount")
    bank_name: str = Field(..., description="Bank name")
    bank_branch: str = Field(..., description="Bank branch")
    bank_account: str = Field(..., description="Bank account number")
    swift_code: str = Field(..., description="SWIFT code")

    class Config:
        json_schema_extra = {
            "example": {
                "check_number": "12345678",
                "amount": 2000.00,
                "bank_name": "Example Bank",
                "bank_branch": "Main Branch",
                "bank_account": "1234567890",
                "swift_code": "EXAMPLEBK"
            }
        }

# Dependency to get service with db session
async def get_payment_service():
    """Async dependency to get payment service with proper session management"""
    session = None
    try:
        session = get_db_session()
        service = AdvancedPaymentService(session)
        yield service
    except Exception as e:
        logger.error(f"Error creating payment service: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize payment service"
        )
    finally:
        if session:
            try:
                session.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}")

@router.post("/divide/{check_id}", response_model=Dict)
async def divide_check(
    check_id: str = Path(..., description="ID of the check to divide"),
    division: CheckDivisionRequest = Body(...),
    service: AdvancedPaymentService = Depends(get_payment_service)
):
    """Divide a check into multiple amounts."""
    try:
        # Validate check exists and can be divided
        check = await service.get_check(check_id)
        if not check:
            raise HTTPException(status_code=404, detail="Check not found")

        if check.status != "pending":
            raise HTTPException(
                status_code=400,
                detail="Only pending checks can be divided"
            )

        # Validate division amounts match check amount
        if division.total_amount != check.amount:
            raise HTTPException(
                status_code=400,
                detail="Sum of division amounts must equal check amount"
            )

        # Perform the division
        result = await service.divide_check(
            check_id=check_id,
            amounts=division.amounts,
            division_date=division.division_date,
            status=division.status
        )

        return {
            "status": "success",
            "message": "Check divided successfully",
            "data": result
        }
    except sqlite3.Error as e:
        logger.error(f"Database error in divide_check: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error dividing check: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during check division"
        )

@router.post("/replace/{old_check_id}", response_model=Dict)
async def replace_check(
    old_check_id: str = Path(..., description="ID of the check to replace"),
    new_check_info: NewCheckInfo = Body(...),
    service: AdvancedPaymentService = Depends(get_payment_service)
):
    """Replace an existing check with a new one."""
    try:
        # Validate old check exists
        old_check = await service.get_check(old_check_id)
        if not old_check:
            raise HTTPException(status_code=404, detail="Original check not found")

        result = await service.replace_check(old_check_id, new_check_info.model_dump())
        return {
            "status": "success",
            "message": "Check replaced successfully",
            "data": result
        }
    except sqlite3.Error as e:
        logger.error(f"Database error in replace_check: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error replacing check: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during check replacement"
        )

@router.get("/unpaid", response_model=Dict)
async def get_unpaid_checks(
    client_id: Optional[str] = Query(None, description="Optional client ID to filter checks"),
    service: AdvancedPaymentService = Depends(get_payment_service)
):
    """Get list of unpaid checks, optionally filtered by client."""
    try:
        checks = await service.track_unpaid_checks(client_id)
        return {
            "status": "success",
            "count": len(checks),
            "data": checks
        }
    except sqlite3.Error as e:
        logger.error(f"Database error in get_unpaid_checks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving unpaid checks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving unpaid checks"
        )

@router.post("/process/{invoice_id}", response_model=Dict)
async def process_check_payment(
    invoice_id: str = Path(..., description="ID of the invoice to process payment for"),
    check_info: CheckPaymentInfo = Body(...),
    service: AdvancedPaymentService = Depends(get_payment_service)
):
    """Process a check payment for an invoice."""
    try:
        # Validate invoice exists
        invoice = await service.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        result = await service.process_check_payment(invoice_id, check_info.model_dump())
        return {
            "status": "success",
            "message": "Check payment processed successfully",
            "data": result
        }
    except sqlite3.Error as e:
        logger.error(f"Database error in process_check_payment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing check payment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during payment processing"
        )

@router.get("/history/{check_number}", response_model=Dict)
async def get_check_history(
    check_number: str = Path(..., description="Check number to get history for"),
    service: AdvancedPaymentService = Depends(get_payment_service)
):
    """Get complete history of a check."""
    try:
        history = await service.get_check_history(check_number)
        if not history:
            raise HTTPException(
                status_code=404,
                detail=f"No history found for check number {check_number}"
            )
        return {
            "status": "success",
            "data": history
        }
    except sqlite3.Error as e:
        logger.error(f"Database error in get_check_history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving check history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving check history"
        )

@router.post("/check-divisions", response_model=Dict)
async def create_check_division(
    division: CheckDivisionRequest = Body(...),
    service: AdvancedPaymentService = Depends(get_payment_service)
):
    """Create a new check division."""
    try:
        result = await service.create_check_division(
            amounts=division.amounts,
            division_date=division.division_date,
            status=division.status
        )
        return {
            "status": "success",
            "message": "Check division created successfully",
            "data": result
        }
    except sqlite3.Error as e:
        logger.error(f"Database error in create_check_division: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating check division: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create check division: {str(e)}"
        )
