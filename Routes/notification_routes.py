from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from enum import Enum

from Services.notification_service import NotificationService, NotificationPriority, NotificationType

router = APIRouter(tags=["notifications"])
notification_service = NotificationService()


# Pydantic models
class NotificationPreferences(BaseModel):
    email_enabled: bool = Field(
        default=True,
        description="Enable email notifications"
    )
    sms_enabled: bool = Field(
        default=False,
        description="Enable SMS notifications"
    )
    in_app_enabled: bool = Field(
        default=True,
        description="Enable in-app notifications"
    )
    notification_types: Dict[str, List[NotificationType]] = Field(
        default=None,
        description="Notification types configuration per category"
    )
    priority_threshold: Dict[str, NotificationPriority] = Field(
        default=None,
        description="Minimum priority threshold per category"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "email_enabled": True,
                "sms_enabled": False,
                "in_app_enabled": True,
                "notification_types": {
                    "invoice": ["IN_APP", "EMAIL"],
                    "payment": ["IN_APP", "SMS", "EMAIL"]
                },
                "priority_threshold": {
                    "invoice": "LOW",
                    "payment": "MEDIUM"
                }
            }
        }
    }

    def __init__(self, **data):
        super().__init__(**data)
        if self.notification_types is None:
            self.notification_types = {}
        if self.priority_threshold is None:
            self.priority_threshold = {}


class NotificationCreate(BaseModel):
    template_key: str = Field(..., description="Key of the notification template to use")
    template_data: Dict = Field(..., description="Data to fill the template")
    notification_type: NotificationType = Field(..., description="Type of notification")
    priority: NotificationPriority = Field(
        default=NotificationPriority.MEDIUM,
        description="Priority level of the notification"
    )
    user_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific users to notify (optional)"
    )
    category: Optional[str] = Field(
        default=None,
        description="Category of the notification"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "template_key": "invoice_processed",
                "template_data": {
                    "invoice_id": "INV-123",
                    "amount": 1000.00
                },
                "notification_type": "IN_APP",
                "priority": "MEDIUM",
                "user_ids": ["user-123", "user-456"],
                "category": "invoice"
            }
        }
    }


class BulkNotificationCreate(BaseModel):
    template_key: str = Field(..., description="Key of the notification template to use")
    template_data_list: List[Dict] = Field(..., description="List of data sets to fill the template")
    notification_type: NotificationType = Field(..., description="Type of notification")
    priority: NotificationPriority = Field(
        default=NotificationPriority.MEDIUM,
        description="Priority level of the notifications"
    )
    user_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific users to notify (optional)"
    )
    category: Optional[str] = Field(
        default=None,
        description="Category of the notifications"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "template_key": "invoice_processed",
                "template_data_list": [
                    {
                        "invoice_id": "INV-123",
                        "amount": 1000.00
                    },
                    {
                        "invoice_id": "INV-124",
                        "amount": 1500.00
                    }
                ],
                "notification_type": "IN_APP",
                "priority": "MEDIUM",
                "user_ids": ["user-123", "user-456"],
                "category": "invoice"
            }
        }
    }


class NotificationTemplate(BaseModel):
    key: str = Field(..., description="Unique key for the template")
    template: str = Field(..., description="Template string with placeholders")

    model_config = {
        "json_schema_extra": {
            "example": {
                "key": "invoice_processed",
                "template": "Invoice {invoice_id} has been processed with amount ${amount}"
            }
        }
    }


@router.post("/notifications", response_model=Dict[str, str])
async def create_notification(notification: NotificationCreate):
    """
    Create a new notification.

    - Uses specified template with provided data
    - Sends to specified users or all users if none specified
    - Respects user notification preferences
    """
    try:
        notification_service.create_notification(
            template_key=notification.template_key,
            template_data=notification.template_data,
            notification_type=notification.notification_type,
            priority=notification.priority,
            user_ids=notification.user_ids,
            category=notification.category
        )
        return {"message": "Notification created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/notifications/bulk", response_model=Dict[str, str])
async def create_bulk_notifications(notification: BulkNotificationCreate):
    """
    Create multiple notifications using the same template.

    - Processes multiple data sets with same template
    - More efficient than creating notifications one by one
    - Returns count of notifications created
    """
    try:
        notification_service.bulk_notify(
            template_key=notification.template_key,
            template_data_list=notification.template_data_list,
            notification_type=notification.notification_type,
            priority=notification.priority,
            user_ids=notification.user_ids,
            category=notification.category
        )
        return {
            "message": f"Bulk notifications created successfully",
            "count": len(notification.template_data_list)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/notifications/templates", response_model=Dict[str, str])
async def add_template(template: NotificationTemplate):
    """
    Add a new notification template.

    - Registers new template for future use
    - Templates can include placeholders for dynamic content
    """
    notification_service.add_template(template.key, template.template)
    return {"message": f"Template '{template.key}' added successfully"}


@router.get("/notifications/templates", response_model=Dict[str, str])
async def get_templates():
    """
    Get all notification templates.

    - Returns all registered templates
    - Includes template keys and their corresponding template strings
    """
    return notification_service.notification_templates


@router.put("/users/{user_id}/notification-preferences", response_model=Dict[str, str])
async def set_user_preferences(
        user_id: str,
        preferences: NotificationPreferences
):
    """
    Set notification preferences for a user.

    - Configure which notification types to receive
    - Set priority thresholds per category
    - Enable/disable different notification channels
    """
    notification_service.set_user_preferences(user_id, preferences.model_dump())
    return {"message": f"Notification preferences updated for user {user_id}"}


@router.get("/users/{user_id}/notification-preferences", response_model=NotificationPreferences)
async def get_user_preferences(user_id: str):
    """
    Get notification preferences for a user.

    - Returns current notification settings
    - Includes enabled channels and priority thresholds
    """
    preferences = notification_service.get_user_preferences(user_id)
    if not preferences:
        raise HTTPException(
            status_code=404,
            detail=f"No notification preferences found for user {user_id}"
        )
    return preferences


# Example usage endpoints
@router.post("/notifications/example/invoice-processed", response_model=Dict[str, str])
async def notify_invoice_processed(
        invoice_id: str,
        user_ids: Optional[List[str]] = Query(None, description="Specific users to notify"),
        notification_type: NotificationType = Query(NotificationType.IN_APP, description="Type of notification to send")
):
    """
    Example endpoint to send invoice processed notification.

    - Demonstrates template usage
    - Shows how to specify recipients
    - Uses low priority for non-critical updates
    """
    notification_service.create_notification(
        template_key="invoice_processed",
        template_data={"invoice_id": invoice_id},
        notification_type=notification_type,
        priority=NotificationPriority.LOW,
        user_ids=user_ids,
        category="invoice"
    )
    return {"message": f"Invoice processed notification sent for invoice {invoice_id}"}


@router.post("/notifications/example/payment-received", response_model=Dict[str, str])
async def notify_payment_received(
        invoice_id: str,
        amount: float,
        user_ids: Optional[List[str]] = Query(None, description="Specific users to notify"),
        notification_type: NotificationType = Query(NotificationType.IN_APP, description="Type of notification to send")
):
    """
    Example endpoint to send payment received notification.

    - Shows how to include multiple data points
    - Uses medium priority for important updates
    - Demonstrates category usage
    """
    notification_service.create_notification(
        template_key="payment_received",
        template_data={"invoice_id": invoice_id, "amount": amount},
        notification_type=notification_type,
        priority=NotificationPriority.MEDIUM,
        user_ids=user_ids,
        category="payment"
    )
    return {"message": f"Payment received notification sent for invoice {invoice_id}"}


@router.post("/notifications/example/stock-alert", response_model=Dict[str, str])
async def notify_stock_alert(
        item: str,
        quantity: int,
        user_ids: Optional[List[str]] = Query(None, description="Specific users to notify"),
        notification_type: NotificationType = Query(NotificationType.IN_APP, description="Type of notification to send")
):
    """
    Example endpoint to send low stock notification.

    - Uses high priority for urgent alerts
    - Shows how to handle numeric data
    - Demonstrates business-critical notifications
    """
    notification_service.create_notification(
        template_key="stock_low",
        template_data={"item": item, "quantity": quantity},
        notification_type=notification_type,
        priority=NotificationPriority.HIGH,
        user_ids=user_ids,
        category="stock"
    )
    return {"message": f"Stock alert notification sent for item {item}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(router, host="0.0.0.0", port=8000)
