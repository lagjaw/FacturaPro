import sys
import os
import logging
from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum
import sqlite3
from Services.communication_service import CommunicationsService
from database import get_db_connection



# Configure logger
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path to allow imports from sibling directories
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Pydantic models
class CommunicationType(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    NOTIFICATION = "notification"


class CommunicationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class CommunicationBase(BaseModel):
    type: CommunicationType
    recipient: str
    subject: Optional[str] = None
    content: str
    priority: Optional[str] = "normal"

    @validator('recipient')
    def validate_recipient(cls, v):
        if not v or not v.strip():
            raise ValueError("Recipient cannot be empty")
        return v.strip()

    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "email",
                "recipient": "user@example.com",
                "subject": "Payment Reminder",
                "content": "Your payment is due soon",
                "priority": "high"
            }
        }
    }


router = APIRouter(
    prefix="/communications",
    tags=["Communications"],
    responses={
        404: {"description": "Resource not found"},
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"}
    }
)


async def get_communication_service():
    """Async dependency to get communication service with proper connection management"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to establish database connection")
            raise HTTPException(
                status_code=500,
                detail="Failed to connect to database"
            )
        service = CommunicationsService(conn)
        yield service
    except Exception as e:
        logger.error(f"Failed to initialize communication service: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize communication service: {str(e)}"
        )
    finally:
        if conn:
            try:
                conn.close()
                logger.debug("Database connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")


@router.post("/send", response_model=Dict, status_code=201)
async def send_communication(
        comm: CommunicationBase,
        service: CommunicationsService = Depends(get_communication_service)
):
    """
    Send a new communication

    Args:
        comm: Communication details including type, recipient, subject, and content

    Returns:
        Dict containing status and communication details
    """
    logger.info(f"Attempting to send {comm.type} communication to {comm.recipient}")
    try:
        result = await service.send_communication(comm)
        logger.info(f"Successfully sent communication: ID {result.get('id')}")
        return {
            "status": "success",
            "data": result
        }
    except sqlite3.Error as e:
        logger.error(f"Database error in send_communication: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Validation error in send_communication: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in send_communication: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send communication: {str(e)}"
        )


@router.get("/history", response_model=Dict)
async def get_communication_history(
        comm_type: Optional[CommunicationType] = Query(None, description="Filter by communication type"),
        status: Optional[CommunicationStatus] = Query(None, description="Filter by status"),
        from_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
        to_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
        service: CommunicationsService = Depends(get_communication_service)
):
    """
    Get communication history with optional filters

    Args:
        comm_type: Optional filter by communication type
        status: Optional filter by status
        from_date: Optional filter by start date
        to_date: Optional filter by end date

    Returns:
        Dict containing list of communications matching the filters
    """
    logger.info("Retrieving communication history with filters")
    try:
        # Validate date formats if provided
        if from_date:
            datetime.strptime(from_date, "%Y-%m-%d")
        if to_date:
            datetime.strptime(to_date, "%Y-%m-%d")

        history = await service.get_history(comm_type, status, from_date, to_date)
        logger.info(f"Retrieved {len(history)} communications")
        return {
            "status": "success",
            "data": history
        }
    except ValueError as e:
        logger.error(f"Invalid date format: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    except sqlite3.Error as e:
        logger.error(f"Database error in get_history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve communication history: {str(e)}"
        )


@router.get("/status/{comm_id}", response_model=Dict)
async def get_communication_status(
        comm_id: str = Path(..., description="ID of the communication to check"),
        service: CommunicationsService = Depends(get_communication_service)
):
    """
    Get status of a specific communication

    Args:
        comm_id: ID of the communication to check

    Returns:
        Dict containing communication status and details
    """
    logger.info(f"Checking status for communication ID: {comm_id}")
    try:
        status = await service.get_status(comm_id)
        logger.info(f"Retrieved status for communication ID {comm_id}")
        return {
            "status": "success",
            "data": status
        }
    except sqlite3.Error as e:
        logger.error(f"Database error in get_status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Communication not found: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get communication status: {str(e)}"
        )


@router.post("/batch", response_model=Dict)
async def send_batch_communications(
        communications: List[CommunicationBase],
        service: CommunicationsService = Depends(get_communication_service)
):
    """
    Send multiple communications in batch

    Args:
        communications: List of communications to send

    Returns:
        Dict containing batch processing results
    """
    logger.info(f"Processing batch of {len(communications)} communications")
    try:
        result = await service.send_batch(communications)
        logger.info(
            f"Batch processing completed: {result['success_count']} successful, {result['failed_count']} failed")
        return {
            "status": "success",
            "data": result
        }
    except sqlite3.Error as e:
        logger.error(f"Database error in send_batch: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in send_batch: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process batch communications: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(router, host="0.0.0.0", port=8000)
