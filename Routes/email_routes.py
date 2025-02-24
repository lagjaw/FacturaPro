from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from Services.email_services import EmailService

# Initialize router
router = APIRouter(
    prefix="/api/email",
    tags=["Email Management"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Initialize email service
SMTP_CONFIG = {
    "host": "smtp.example.com",
    "port": 587,
    "username": "your_username",
    "password": "your_password",
    "use_tls": True,
    "from_email": "noreply@example.com"
}

email_service = EmailService(SMTP_CONFIG)


# Pydantic models for request validation
class EmailRequest(BaseModel):
    to_emails: List[EmailStr] = Field(..., description="List of recipient email addresses")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Plain text email body")
    html_body: Optional[str] = Field(None, description="HTML version of email body")
    cc: Optional[List[EmailStr]] = Field(None, description="List of CC recipients")
    bcc: Optional[List[EmailStr]] = Field(None, description="List of BCC recipients")

    model_config = {
        "json_schema_extra": {
            "example": {
                "to_emails": ["recipient@example.com"],
                "subject": "Test Email",
                "body": "This is a test email",
                "html_body": "<h1>This is a test email</h1>",
                "cc": ["cc@example.com"],
                "bcc": ["bcc@example.com"]
            }
        }
    }


class TemplateEmailRequest(BaseModel):
    to_emails: List[EmailStr] = Field(..., description="List of recipient email addresses")
    template_name: str = Field(..., description="Name of the email template to use")
    template_data: Dict = Field(..., description="Data to fill the template")
    subject: str = Field(..., description="Email subject")
    cc: Optional[List[EmailStr]] = Field(None, description="List of CC recipients")
    bcc: Optional[List[EmailStr]] = Field(None, description="List of BCC recipients")

    model_config = {
        "json_schema_extra": {
            "example": {
                "to_emails": ["recipient@example.com"],
                "template_name": "welcome_email",
                "template_data": {"user_name": "John Doe"},
                "subject": "Welcome to our service",
                "cc": ["cc@example.com"],
                "bcc": ["bcc@example.com"]
            }
        }
    }


class BulkEmailRequest(BaseModel):
    emails: List[EmailRequest] = Field(..., description="List of emails to send")

    model_config = {
        "json_schema_extra": {
            "example": {
                "emails": [
                    {
                        "to_emails": ["recipient1@example.com"],
                        "subject": "Test Email 1",
                        "body": "This is test email 1"
                    },
                    {
                        "to_emails": ["recipient2@example.com"],
                        "subject": "Test Email 2",
                        "body": "This is test email 2"
                    }
                ]
            }
        }
    }


@router.post("/send", response_model=Dict[str, bool])
async def send_email(email_request: EmailRequest):
    """
    Send an email to specified recipients.

    - Supports both plain text and HTML content
    - Allows CC and BCC recipients
    - Returns success status of the operation
    """
    try:
        success = email_service.send_email(
            to_emails=email_request.to_emails,
            subject=email_request.subject,
            body=email_request.body,
            html_body=email_request.html_body,
            cc=email_request.cc,
            bcc=email_request.bcc
        )
        return {"success": success}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error sending email: {str(e)}"
        )


@router.post("/send-template", response_model=Dict[str, bool])
async def send_template_email(template_request: TemplateEmailRequest):
    """
    Send an email using a template.

    - Uses specified template with provided data
    - Supports CC and BCC recipients
    - Returns success status of the operation
    """
    try:
        success = email_service.send_template_email(
            to_emails=template_request.to_emails,
            template_name=template_request.template_name,
            template_data=template_request.template_data,
            subject=template_request.subject,
            cc=template_request.cc,
            bcc=template_request.bcc
        )
        return {"success": success}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error sending template email: {str(e)}"
        )


@router.post("/send-bulk", response_model=Dict[str, int])
async def send_bulk_emails(bulk_request: BulkEmailRequest):
    """
    Send multiple emails in bulk.

    - Processes multiple emails in a single request
    - Returns count of successful and failed emails
    - Continues processing even if some emails fail
    """
    try:
        email_data = [
            {
                "to_emails": email.to_emails,
                "subject": email.subject,
                "body": email.body,
                "html_body": email.html_body,
                "cc": email.cc,
                "bcc": email.bcc
            }
            for email in bulk_request.emails
        ]
        return email_service.send_bulk_emails(email_data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error sending bulk emails: {str(e)}"
        )


@router.post("/validate", response_model=Dict[str, List[str]])
async def validate_emails(
        emails: List[str] = Body(..., examples=[["test@example.com", "invalid-email"]])
):
    """
    Validate a list of email addresses.

    - Checks format of email addresses
    - Returns lists of valid and invalid addresses
    - Does not verify if emails actually exist
    """
    try:
        results = email_service.validate_email_addresses(emails)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validating emails: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(router, host="0.0.0.0", port=8000)
