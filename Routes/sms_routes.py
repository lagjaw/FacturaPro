from fastapi import APIRouter, HTTPException, Body, Query
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from Services.sms_services import SMSService

# Configuration SMS (à charger depuis les variables d'environnement en production)
SMS_CONFIG = {
    "provider": "mock_provider",
    "api_key": "mock_api_key",
    "api_secret": "mock_api_secret",
    "from_number": "+1234567890"
}

router = APIRouter(tags=["sms"])
sms_service = SMSService(SMS_CONFIG)


# Pydantic models
class SMSMessage(BaseModel):
    to_numbers: List[str] = Field(..., description="List of recipient phone numbers")
    message: str = Field(..., description="SMS message content")
    priority: str = Field("normal", description="Message priority (normal, high)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "to_numbers": ["+1234567890", "+0987654321"],
                "message": "Your order has been processed",
                "priority": "normal"
            }
        }
    }


class BulkSMSMessage(BaseModel):
    messages: List[SMSMessage] = Field(..., description="List of SMS messages to send")

    model_config = {
        "json_schema_extra": {
            "example": {
                "messages": [
                    {
                        "to_numbers": ["+1234567890"],
                        "message": "First message",
                        "priority": "normal"
                    },
                    {
                        "to_numbers": ["+0987654321"],
                        "message": "Second message",
                        "priority": "high"
                    }
                ]
            }
        }
    }


class ScheduledSMS(BaseModel):
    to_numbers: List[str] = Field(..., description="List of recipient phone numbers")
    message: str = Field(..., description="SMS message content")
    send_at: datetime = Field(..., description="DateTime when the message should be sent")
    priority: str = Field("normal", description="Message priority (normal, high)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "to_numbers": ["+1234567890"],
                "message": "Scheduled message",
                "send_at": "2024-12-31T12:00:00",
                "priority": "normal"
            }
        }
    }


@router.post("/sms/send", response_model=Dict)
async def send_sms(message: SMSMessage):
    """
    Send an SMS message to one or more recipients.

    - Validates phone numbers
    - Sends message with specified priority
    - Returns sending status and details
    """
    try:
        # Validate phone numbers first
        validation = sms_service.validate_phone_numbers(message.to_numbers)
        if validation["invalid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid phone numbers: {', '.join(validation['invalid'])}"
            )

        result = sms_service.send_sms(
            to_numbers=message.to_numbers,
            message=message.message,
            priority=message.priority
        )

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to send SMS")
            )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send SMS: {str(e)}"
        )


@router.post("/sms/bulk", response_model=Dict[str, int])
async def send_bulk_sms(bulk_message: BulkSMSMessage):
    """
    Send multiple SMS messages in bulk.

    - Processes multiple messages in a single request
    - Returns count of successful and failed messages
    - Continues processing even if some messages fail
    """
    try:
        messages = [
            {
                "to_numbers": msg.to_numbers,
                "message": msg.message,
                "priority": msg.priority
            }
            for msg in bulk_message.messages
        ]

        return sms_service.send_bulk_sms(messages)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send bulk SMS: {str(e)}"
        )


@router.post("/sms/validate", response_model=Dict[str, List[str]])
async def validate_phone_numbers(
        phone_numbers: List[str] = Body(..., example=["+1234567890", "invalid-number"])
):
    """
    Validate a list of phone numbers.

    - Checks format of phone numbers
    - Returns lists of valid and invalid numbers
    - Does not send any messages
    """
    try:
        return sms_service.validate_phone_numbers(phone_numbers)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate phone numbers: {str(e)}"
        )


@router.get("/sms/status/{message_id}", response_model=Dict)
async def get_message_status(message_id: str):
    """
    Get the status of a sent message.

    - Returns current status of the message
    - Includes delivery timestamp if available
    - Shows recipient count
    """
    try:
        return sms_service.get_message_status(message_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get message status: {str(e)}"
        )


@router.post("/sms/schedule", response_model=Dict)
async def schedule_sms(scheduled_message: ScheduledSMS):
    """
    Schedule an SMS to be sent at a specific time.

    - Validates phone numbers
    - Schedules message for future delivery
    - Returns scheduling confirmation
    """
    try:
        # Validate phone numbers first
        validation = sms_service.validate_phone_numbers(scheduled_message.to_numbers)
        if validation["invalid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid phone numbers: {', '.join(validation['invalid'])}"
            )

        # Ensure scheduled time is in the future
        if scheduled_message.send_at <= datetime.now():
            raise HTTPException(
                status_code=400,
                detail="Scheduled time must be in the future"
            )

        result = sms_service.schedule_sms(
            to_numbers=scheduled_message.to_numbers,
            message=scheduled_message.message,
            send_at=scheduled_message.send_at,
            priority=scheduled_message.priority
        )

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to schedule SMS")
            )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to schedule SMS: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(router, host="0.0.0.0", port=8000)
