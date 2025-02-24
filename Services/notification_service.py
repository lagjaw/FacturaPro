from typing import Optional, Dict, List
from datetime import datetime
from Services.alert_service import AlertService
from Services.email_services import EmailService
from Services.sms_services import SMSService
from enum import Enum


class NotificationType(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationService:
    def __init__(self, email_config: Optional[Dict] = None, sms_config: Optional[Dict] = None):
        self.alert_service = AlertService()
        self.email_service = EmailService(email_config)
        self.sms_service = SMSService(sms_config)
        self.notification_settings: Dict[str, Dict] = {}  # User notification preferences
        self.notification_templates: Dict[str, str] = {
            "invoice_processed": "Invoice {invoice_id} has been processed successfully",
            "payment_received": "Payment of {amount} received for invoice {invoice_id}",
            "stock_low": "Low stock alert: {item} ({quantity} remaining)",
            "payment_overdue": "Payment overdue for invoice {invoice_id}",
        }

    def set_user_preferences(self, user_id: str, preferences: Dict):
        """
        Set notification preferences for a user
        Args:
            user_id: User identifier
            preferences: Dict containing notification preferences
        """
        self.notification_settings[user_id] = preferences

    def get_user_preferences(self, user_id: str) -> Dict:
        """
        Get notification preferences for a user
        """
        return self.notification_settings.get(user_id, {})

    def create_notification(
            self,
            template_key: str,
            template_data: Dict,
            notification_type: NotificationType,
            priority: NotificationPriority = NotificationPriority.MEDIUM,
            user_ids: Optional[List[str]] = None,
            category: Optional[str] = None,
            subject: Optional[str] = None
    ):
        """
        Create a notification using a template
        Args:
            template_key: Key for the notification template
            template_data: Data to fill the template
            notification_type: Type of notification (in_app, email, sms)
            priority: Priority level of the notification
            user_ids: List of user IDs to notify
            category: Category of the notification
            subject: Email subject (only for email notifications)
        """
        if template_key not in self.notification_templates:
            raise ValueError(f"Template {template_key} not found")

        message = self.notification_templates[template_key].format(**template_data)

        # Create in-app alert if notification type is IN_APP
        if notification_type == NotificationType.IN_APP:
            level = self._priority_to_level(priority)
            self.alert_service.add_alert(message, level, category)

        # Handle email notifications
        elif notification_type == NotificationType.EMAIL:
            if not user_ids:
                raise ValueError("User IDs required for email notifications")

            email_addresses = self._get_user_email_addresses(user_ids)
            if not email_addresses:
                raise ValueError("No valid email addresses found for users")

            email_subject = subject or f"{category.title() if category else 'Notification'}: {template_key.replace('_', ' ').title()}"

            self.email_service.send_email(
                to_emails=email_addresses,
                subject=email_subject,
                body=message,
                html_body=self._create_html_email(message, category, priority)
            )

        # Handle SMS notifications
        elif notification_type == NotificationType.SMS:
            if not user_ids:
                raise ValueError("User IDs required for SMS notifications")

            phone_numbers = self._get_user_phone_numbers(user_ids)
            if not phone_numbers:
                raise ValueError("No valid phone numbers found for users")

            self.sms_service.send_sms(
                to_numbers=phone_numbers,
                message=message,
                priority=priority.value
            )

    def add_template(self, key: str, template: str):
        """
        Add a new notification template
        Args:
            key: Template identifier
            template: Template string with placeholders
        """
        self.notification_templates[key] = template

    def _priority_to_level(self, priority: NotificationPriority) -> str:
        """Convert notification priority to alert level"""
        priority_level_map = {
            NotificationPriority.LOW: "info",
            NotificationPriority.MEDIUM: "info",
            NotificationPriority.HIGH: "warning",
            NotificationPriority.URGENT: "error"
        }
        return priority_level_map[priority]

    def _create_html_email(self, message: str, category: Optional[str], priority: NotificationPriority) -> str:
        """Create HTML version of email message"""
        priority_colors = {
            NotificationPriority.LOW: "#28a745",
            NotificationPriority.MEDIUM: "#ffc107",
            NotificationPriority.HIGH: "#fd7e14",
            NotificationPriority.URGENT: "#dc3545"
        }

        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    {f'<div style="margin-bottom: 10px; color: #666;">Category: {category}</div>' if category else ''}
                    <div style="margin-bottom: 20px; padding: 15px; background-color: {priority_colors[priority]}; color: white; border-radius: 5px;">
                        Priority: {priority.value}
                    </div>
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
                        {message}
                    </div>
                    <div style="margin-top: 20px; font-size: 12px; color: #666;">
                        Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </div>
                </div>
            </body>
        </html>
        """

    def _get_user_email_addresses(self, user_ids: List[str]) -> List[str]:
        """
        Get email addresses for users
        This is a placeholder method - implement actual user email lookup
        """
        # In a real application, you would lookup user email addresses
        # from your user management system
        return [f"user_{uid}@example.com" for uid in user_ids]

    def _get_user_phone_numbers(self, user_ids: List[str]) -> List[str]:
        """
        Get phone numbers for users
        This is a placeholder method - implement actual user phone lookup
        """
        # In a real application, you would lookup user phone numbers
        # from your user management system
        return [f"+1555{uid.zfill(8)}" for uid in user_ids]

    def bulk_notify(
            self,
            template_key: str,
            template_data_list: List[Dict],
            notification_type: NotificationType,
            priority: NotificationPriority = NotificationPriority.MEDIUM,
            user_ids: Optional[List[str]] = None,
            category: Optional[str] = None
    ):
        """
        Send multiple notifications using the same template
        Args:
            template_key: Key for the notification template
            template_data_list: List of data dicts to fill the template
            notification_type: Type of notification
            priority: Priority level
            user_ids: List of user IDs to notify
            category: Category of the notifications
        """
        for template_data in template_data_list:
            self.create_notification(
                template_key,
                template_data,
                notification_type,
                priority,
                user_ids,
                category
            )
