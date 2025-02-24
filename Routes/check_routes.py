from fastapi import APIRouter, HTTPException, Body, Path
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from enum import Enum

from Services.check_service import CheckService

router = APIRouter(tags=["checks"])
check_service = CheckService()

# Enums for validation
class CheckStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    CANCELLED = "cancelled"
    BOUNCED = "bounced"
    REPLACED = "replaced"

# Pydantic models
class CheckCreate(BaseModel):
    transaction_id: str = Field(..., description="ID of the associated transaction")
    check_number: str = Field(..., description="Check number")
    amount: float = Field(..., gt=0, description="Check amount")
    status: CheckStatus = Field(default=CheckStatus.PENDING, description="Check status")
    check_date: str = Field(..., description="Date of the check")
    bank_name: str = Field(..., description="Name of the bank")
    bank_branch: str = Field(..., description="Bank branch")
    bank_account: str = Field(..., description="Bank account number")
    swift_code: str = Field(..., description="SWIFT code")

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "check_number": "1234567",
                "amount": 1000.00,
                "status": "pending",
                "check_date": "2025-02-01",
                "bank_name": "Example Bank",
                "bank_branch": "Main Branch",
                "bank_account": "123456789",
                "swift_code": "EXAMPLEBK"
            }
        }
    }

class CheckStatusUpdate(BaseModel):
    status: CheckStatus = Field(..., description="New status for the check")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "processed"
            }
        }
    }

@router.post("/checks", response_model=dict)
async def create_check(check: CheckCreate):
    """
    Create a new check in the system.

    - Creates a new check with the provided details
    - Returns the ID of the newly created check
    """
    try:
        check_id = check_service.create_check(
            transaction_id=check.transaction_id,
            check_number=check.check_number,
            amount=check.amount,
            status=check.status.value,
            check_date=check.check_date,
            bank_name=check.bank_name,
            bank_branch=check.bank_branch,
            bank_account=check.bank_account,
            swift_code=check.swift_code
        )
        return {
            "status": "success",
            "message": "Check created successfully",
            "check_id": check_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create check: {str(e)}"
        )

@router.put("/checks/{check_id}/status", response_model=dict)
async def update_check_status(
        check_id: str = Path(..., description="ID of the check to update"),
        status_update: CheckStatusUpdate = Body(...)
):
    """
    Update the status of an existing check.

    - Updates the status of the specified check
    - Records the update timestamp
    """
    try:
        check_service.update_check_status(
            check_id=check_id,
            status=status_update.status.value,
            updated_at=datetime.now().isoformat()
        )
        return {
            "status": "success",
            "message": "Check status updated successfully",
            "check_id": check_id,
            "new_status": status_update.status
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update check status: {str(e)}"
        )

@router.get("/checks/status/{status}", response_model=dict)
async def get_checks_by_status(
        status: CheckStatus = Path(..., description="Status to filter checks by")
):
    """
    Get all checks with a specific status.

    - Returns list of checks matching the specified status
    - Useful for monitoring and reporting
    """
    try:
        checks = check_service.get_checks_by_status(status.value)
        return {
            "status": "success",
            "filter_status": status.value,
            "checks": checks
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get checks: {str(e)}"
        )

@router.get("/checks/transaction/{transaction_id}", response_model=dict)
async def get_checks_by_transaction(
        transaction_id: str = Path(..., description="Transaction ID to get checks for")
):
    """
    Get all checks associated with a specific transaction.

    - Returns list of checks for the specified transaction
    - Useful for transaction management
    """
    try:
        checks = check_service.get_checks_by_transaction(transaction_id)
        return {
            "status": "success",
            "transaction_id": transaction_id,
            "checks": checks
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get checks: {str(e)}"
        )

@router.get("/checks/{check_id}", response_model=dict)
async def get_check_details(
        check_id: str = Path(..., description="ID of the check to retrieve")
):
    """
    Get detailed information about a specific check.

    - Returns all details of the specified check
    - Includes transaction and status history
    """
    try:
        details = check_service.get_check_details(check_id)
        return {
            "status": "success",
            "check_id": check_id,
            "details": details
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get check details: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(router, host="0.0.0.0", port=8000)
