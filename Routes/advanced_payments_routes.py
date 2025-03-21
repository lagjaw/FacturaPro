from fastapi import APIRouter, HTTPException, Body, Path, Query, Depends
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from Models.Invoice import Invoice
from Services.advanced_payment_service import AdvancedPaymentService
from database import get_db_session
import logging
from Models.Check import Check

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()
advanced_payments_router = router

# Pydantic models
class CheckDivisionRequest(BaseModel):
    amounts: List[float] = Field(..., description="List of amounts for the division")

    @property
    def total_amount(self) -> float:
        return sum(self.amounts)

    class Config:
        json_schema_extra = {"examples": [{"amounts": [3000, 2000]}]}


class NewCheckInfo(BaseModel):
    check_number: str = Field(..., description="New check number")
    amount: float = Field(..., gt=0, description="Check amount")
    bank_name: str = Field(..., description="Bank name")
    bank_branch: str = Field(..., description="Bank branch")
    bank_account: str = Field(..., description="Bank account number")
    swift_code: str = Field(..., description="SWIFT code")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "check_number": "12345678",
                    "amount": 2000.00,
                    "bank_name": "Example Bank",
                    "bank_branch": "Main Branch",
                    "bank_account": "1234567890",
                    "swift_code": "EXAMPLEBK",
                }
            ]
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
            "examples": [
                {
                    "check_number": "12345678",
                    "amount": 2000.00,
                    "bank_name": "Example Bank",
                    "bank_branch": "Main Branch",
                    "bank_account": "1234567890",
                    "swift_code": "EXAMPLEBK",
                }
            ]
        }


def get_payment_service():
    """Dependency to retrieve an instance of AdvancedPaymentService."""
    return AdvancedPaymentService()  # No session passed here

@router.post("/divide/{check_id}", response_model=Dict)
async def divide_check(
    check_id: str = Path(..., description="ID of the check to divide"),
    division: CheckDivisionRequest = Body(...),
    service: AdvancedPaymentService = Depends(get_payment_service),
):
    """Divide a check into multiple amounts."""
    logger.info(f"Received request to divide check ID: {check_id} with amounts: {division.amounts}")

    try:
        result = await service.divide_check(check_id, division.amounts)  # Await the async method
        return {"status": "success", "message": "Check divided successfully", "data": result}
    except ValueError as e:
        logger.error(f"ValueError in divide_check: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in divide_check: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during check division")


@router.post("/replace/{old_check_id}", response_model=Dict)
async def replace_check(
    old_check_id: str = Path(..., description="ID of the check to replace"),
    new_check_info: NewCheckInfo = Body(...),
    service: AdvancedPaymentService = Depends(get_payment_service),
):
    """Replace an existing check with a new one."""
    logger.info(f"Received request to replace check ID: {old_check_id} with new info: {new_check_info}")

    try:
        result = await service.replace_check(old_check_id, new_check_info.dict())  # Await the async method
        return {"status": "success", "message": "Check replaced successfully", "data": result}
    except ValueError as e:
        logger.error(f"ValueError in replace_check: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error replacing check: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during check replacement")


@router.get("/unpaid", response_model=Dict)
async def get_unpaid_checks(
    client_id: Optional[str] = Query(None, description="Optional client ID to filter checks"),
    service: AdvancedPaymentService = Depends(get_payment_service),
):
    """Get list of unpaid checks, optionally filtered by client."""
    logger.info(f"Received request to get unpaid checks with client ID: {client_id}")

    try:
        checks = await service.track_unpaid_checks(client_id)  # Await the async method
        return {"status": "success", "count": len(checks), "data": checks}
    except Exception as e:
        logger.error(f"Error retrieving unpaid checks: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while retrieving unpaid checks")


@router.post("/process/{invoice_id}", response_model=Dict)
async def process_check_payment(
    invoice_id: str = Path(..., description="ID of the invoice to process payment for"),
    check_info: CheckPaymentInfo = Body(...),
    service: AdvancedPaymentService = Depends(get_payment_service),
):
    """Process a check payment for an invoice."""
    logger.info(f"Received request to process payment for invoice ID: {invoice_id} with check info: {check_info}")

    try:
        result = await service.process_check_payment(invoice_id, check_info.dict())  # Await the async method
        return {"status": "success", "message": "Check payment processed successfully", "data": result}
    except ValueError as e:
        logger.error(f"ValueError in process_check_payment: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing check payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during payment processing")


@router.get("/history/{check_number}", response_model=Dict)
async def get_check_history(
    check_number: str = Path(..., description="Check number to get history for"),
    service: AdvancedPaymentService = Depends(get_payment_service),
):
    """Get complete history of a check."""
    logger.info(f"Received request to get history for check number: {check_number}")

    try:
        history = await service.get_check_history(check_number)  # Await the async method
        if not history:
            raise HTTPException(status_code=404, detail=f"No history found for check number {check_number}")

        return {"status": "success", "data": history}
    except ValueError as e:
        logger.error(f"ValueError in get_check_history: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving check history: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while retrieving check history")