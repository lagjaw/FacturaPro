from fastapi import APIRouter, HTTPException, Body, Path
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from enum import Enum

from Services.checkDivision_service import CheckDivisionService

router = APIRouter(tags=["check-divisions"])
check_division_service = CheckDivisionService()

# Enums for validation
class DivisionStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"

# Pydantic models
class CheckDivisionCreate(BaseModel):
    check_id: str = Field(..., description="ID of the check to divide")
    amount: float = Field(..., gt=0, description="Amount of the division")
    division_date: str = Field(..., description="Date of the division")
    status: DivisionStatus = Field(default=DivisionStatus.PENDING, description="Division status")

    model_config = {
        "json_schema_extra": {
            "example": {
                "check_id": "123e4567-e89b-12d3-a456-426614174000",
                "amount": 500.00,
                "division_date": "2025-02-01",
                "status": "pending"
            }
        }
    }

class DivisionStatusUpdate(BaseModel):
    status: DivisionStatus = Field(..., description="New status for the division")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "processed"
            }
        }
    }

@router.post("/check-divisions", response_model=dict)
async def create_check_division(division: CheckDivisionCreate):
    """
    Create a new check division.

    - Creates a new division for an existing check
    - Returns the ID of the newly created division
    """
    try:
        division_id = check_division_service.create_check_division(
            check_id=division.check_id,
            amount=division.amount,
            division_date=division.division_date,
            status=division.status.value
        )
        return {
            "status": "success",
            "message": "Check division created successfully",
            "division_id": division_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create check division: {str(e)}"
        )

@router.put("/check-divisions/{division_id}/status", response_model=dict)
async def update_division_status(
        division_id: str = Path(..., description="ID of the division to update"),
        status_update: DivisionStatusUpdate = Body(...)
):
    """
    Update the status of an existing check division.

    - Updates the status of the specified division
    - Records the update timestamp
    """
    try:
        check_division_service.update_check_division_status(
            division_id=division_id,
            status=status_update.status.value,
            updated_at=datetime.now().isoformat()
        )
        return {
            "status": "success",
            "message": "Check division status updated successfully",
            "division_id": division_id,
            "new_status": status_update.status
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update division status: {str(e)}"
        )

@router.get("/check-divisions/check/{check_id}", response_model=dict)
async def get_divisions_by_check(
        check_id: str = Path(..., description="Check ID to get divisions for")
):
    """
    Get all divisions for a specific check.

    - Returns list of divisions for the specified check
    - Useful for tracking check divisions
    """
    try:
        divisions = check_division_service.get_divisions_by_check(check_id)
        return {
            "status": "success",
            "check_id": check_id,
            "divisions": divisions
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get divisions: {str(e)}"
        )

@router.get("/check-divisions/status/{status}", response_model=dict)
async def get_divisions_by_status(
        status: DivisionStatus = Path(..., description="Status to filter divisions by")
):
    """
    Get all divisions with a specific status.

    - Returns list of divisions matching the specified status
    - Useful for monitoring and reporting
    """
    try:
        divisions = check_division_service.get_divisions_by_status(status.value)
        return {
            "status": "success",
            "filter_status": status.value,
            "divisions": divisions
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get divisions: {str(e)}"
        )

@router.get("/check-divisions/{division_id}", response_model=dict)
async def get_division_details(
        division_id: str = Path(..., description="ID of the division to retrieve")
):
    """
    Get detailed information about a specific check division.

    - Returns all details of the specified division
    - Includes status history and related check information
    """
    try:
        details = check_division_service.get_division_details(division_id)
        return {
            "status": "success",
            "division_id": division_id,
            "details": details
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get division details: {str(e)}"
        )

@router.post("/check-divisions/validate", response_model=dict)
async def validate_division(division: CheckDivisionCreate):
    """
    Validate a potential check division before creating it.

    - Validates if the division amount is valid for the check
    - Checks if the check can be divided
    - Returns validation result
    """
    try:
        validation_result = check_division_service.validate_division(
            check_id=division.check_id,
            amount=division.amount,
            division_date=division.division_date
        )
        return {
            "status": "success",
            "valid": True,
            "details": validation_result
        }
    except ValueError as e:
        return {
            "status": "success",
            "valid": False,
            "reason": str(e)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )
