from typing import List, Optional, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import logging
from datetime import datetime


class EmailService:
    def __init__(self, smtp_config: Optional[Dict] = None):
        """
        Initialize EmailService with SMTP configuration
        Args:
            smtp_config: Dictionary containing SMTP configuration
                {
                    "host": str,
                    "port": int,
                    "username": str,
                    "password": str,
                    "use_tls": bool,
                    "from_email": str
                }
        """
        self.smtp_config = smtp_config or {}
        self.logger = logging.getLogger(__name__)
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging for email service"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def send_email(
            self,
            to_emails: List[str],
            subject: str,
            body: str,
            html_body: Optional[str] = None,
            cc: Optional[List[str]] = None,
            bcc: Optional[List[str]] = None,
            attachments: Optional[List[Dict]] = None
    ) -> bool:
        """
        Send email to recipients
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body: Plain text email body
            html_body: HTML version of email body (optional)
            cc: List of CC recipients (optional)
            bcc: List of BCC recipients (optional)
            attachments: List of attachment dictionaries (optional)
                [{"filename": str, "content": bytes, "content_type": str}]
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not self.smtp_config:
            self.logger.error("SMTP configuration not provided")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_config.get('from_email', 'noreply@example.com')
            msg['To'] = ', '.join(to_emails)

            if cc:
                msg['Cc'] = ', '.join(cc)
            if bcc:
                msg['Bcc'] = ', '.join(bcc)

            # Add plain text body
            msg.attach(MIMEText(body, 'plain'))

            # Add HTML body if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))

            # Connect to SMTP server
            with smtplib.SMTP(
                    self.smtp_config['host'],
                    self.smtp_config['port']
            ) as server:
                if self.smtp_config.get('use_tls', True):
                    server.starttls()

                if self.smtp_config.get('username') and self.smtp_config.get('password'):
                    server.login(
                        self.smtp_config['username'],
                        self.smtp_config['password']
                    )

                # Combine all recipients
                all_recipients = to_emails + (cc or []) + (bcc or [])

                # Send email
                server.send_message(msg)

                self.logger.info(
                    f"Email sent successfully to {len(all_recipients)} recipients"
                )
                return True

        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
            return False

    def send_template_email(
            self,
            to_emails: List[str],
            template_name: str,
            template_data: Dict,
            subject: str,
            cc: Optional[List[str]] = None,
            bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send email using a template
        Args:
            to_emails: List of recipient email addresses
            template_name: Name of the email template to use
            template_data: Dictionary of data to fill template
            subject: Email subject
            cc: List of CC recipients (optional)
            bcc: List of BCC recipients (optional)
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # This is a placeholder for template rendering
            # In a real application, you would load and render the template
            # using a template engine like Jinja2
            body = f"Template: {template_name}\nData: {template_data}"
            html_body = f"<h1>Template: {template_name}</h1><pre>{template_data}</pre>"

            return self.send_email(
                to_emails=to_emails,
                subject=subject,
                body=body,
                html_body=html_body,
                cc=cc,
                bcc=bcc
            )

        except Exception as e:
            self.logger.error(f"Failed to send template email: {str(e)}")
            return False

    def send_bulk_emails(
            self,
            email_data: List[Dict]
    ) -> Dict[str, int]:
        """
        Send multiple emails in bulk
        Args:
            email_data: List of dictionaries containing email data
                [{
                    "to_emails": List[str],
                    "subject": str,
                    "body": str,
                    "html_body": Optional[str],
                    "cc": Optional[List[str]],
                    "bcc": Optional[List[str]]
                }]
        Returns:
            Dict containing counts of successful and failed emails
        """
        results = {"successful": 0, "failed": 0}

        for email in email_data:
            success = self.send_email(
                to_emails=email["to_emails"],
                subject=email["subject"],
                body=email["body"],
                html_body=email.get("html_body"),
                cc=email.get("cc"),
                bcc=email.get("bcc")
            )

            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1

        self.logger.info(
            f"Bulk email sending completed. "
            f"Successful: {results['successful']}, "
            f"Failed: {results['failed']}"
        )
        return results

    def validate_email_address(self, email: str) -> bool:
        """
        Basic email address validation
        Args:
            email: Email address to validate
        Returns:
            bool: True if email appears valid, False otherwise
        """
        # This is a very basic validation
        # In a production environment, you might want to use a more robust solution
        return '@' in email and '.' in email.split('@')[1]

    def validate_email(self, emails: List[str]) -> Dict[str, List[str]]:
        """
        Validate a list of email addresses
        Args:
            emails: List of email addresses to validate
        Returns:
            Dict containing valid and invalid email addresses
        """
        result = {"valid": [], "invalid": []}

        for email in emails:
            if self.validate_email_address(email):
                result["valid"].append(email)
            else:
                result["invalid"].append(email)

        return result
