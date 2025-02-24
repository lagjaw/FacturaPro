from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
from fastapi import HTTPException
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
)
logger = logging.getLogger(__name__)


class CommunicationsService:
    def __init__(self, db_path: str = "factu_pro.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Creates and returns a database connection."""
        return sqlite3.connect(self.db_path)

    def init_db(self) -> None:
        """Initialize database tables for communications."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create email_history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_history (
                    id TEXT PRIMARY KEY,
                    recipients TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    sent_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create sms_history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sms_history (
                    id TEXT PRIMARY KEY,
                    recipients TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    sent_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create communications_config table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS communications_config (
                    id TEXT PRIMARY KEY,
                    smtp_server TEXT,
                    smtp_port INTEGER,
                    smtp_user TEXT,
                    smtp_password TEXT,
                    sms_provider TEXT,
                    sms_api_key TEXT,
                    sms_sender_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()

    async def send_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send an email and record it in history."""
        try:
            # Get SMTP configuration
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM communications_config LIMIT 1")
                config = cursor.fetchone()

            if not config:
                raise HTTPException(
                    status_code=400,
                    detail="Email configuration not found"
                )

            # Create email message
            msg = MIMEMultipart()
            msg['From'] = config[3]  # smtp_user
            msg['To'] = ", ".join(email_data['recipients'])
            msg['Subject'] = email_data['subject']
            msg.attach(MIMEText(email_data['message'], 'plain'))

            # Send email
            with smtplib.SMTP(config[1], config[2]) as server:  # smtp_server, smtp_port
                server.starttls()
                server.login(config[3], config[4])  # smtp_user, smtp_password
                server.send_message(msg)

            # Record in history
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO email_history (
                        id, recipients, subject, message, status, sent_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().strftime('%Y%m%d%H%M%S'),
                    ','.join(email_data['recipients']),
                    email_data['subject'],
                    email_data['message'],
                    'sent',
                    datetime.now().isoformat()
                ))
                conn.commit()

            return {"status": "success", "message": "Email sent successfully"}

        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error sending email: {str(e)}"
            )

    async def send_sms(self, sms_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send SMS and record it in history."""
        try:
            # Get SMS configuration
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM communications_config LIMIT 1")
                config = cursor.fetchone()

            if not config:
                raise HTTPException(
                    status_code=400,
                    detail="SMS configuration not found"
                )

            # TODO: Implement SMS sending logic based on provider
            # For now, just record in history
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sms_history (
                        id, recipients, message, status, sent_at
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    datetime.now().strftime('%Y%m%d%H%M%S'),
                    ','.join(sms_data['recipients']),
                    sms_data['message'],
                    'sent',
                    datetime.now().isoformat()
                ))
                conn.commit()

            return {"status": "success", "message": "SMS sent successfully"}

        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error sending SMS: {str(e)}"
            )

    async def get_email_history(self) -> List[Dict[str, Any]]:
        """Get email sending history."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM email_history ORDER BY created_at DESC")
                columns = [description[0] for description in cursor.description]
                results = cursor.fetchall()

                return [dict(zip(columns, row)) for row in results]

        except Exception as e:
            logger.error(f"Error getting email history: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting email history: {str(e)}"
            )

    async def get_sms_history(self) -> List[Dict[str, Any]]:
        """Get SMS sending history."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM sms_history ORDER BY created_at DESC")
                columns = [description[0] for description in cursor.description]
                results = cursor.fetchall()

                return [dict(zip(columns, row)) for row in results]

        except Exception as e:
            logger.error(f"Error getting SMS history: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting SMS history: {str(e)}"
            )

    async def update_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update communications configuration."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Delete existing config
                cursor.execute("DELETE FROM communications_config")

                # Insert new config
                cursor.execute('''
                    INSERT INTO communications_config (
                        id, smtp_server, smtp_port, smtp_user, smtp_password,
                        sms_provider, sms_api_key, sms_sender_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().strftime('%Y%m%d%H%M%S'),
                    config_data['email']['smtp_server'],
                    config_data['email']['smtp_port'],
                    config_data['email']['smtp_user'],
                    config_data['email']['smtp_password'],
                    config_data['sms']['provider'],
                    config_data['sms']['api_key'],
                    config_data['sms']['sender_id']
                ))
                conn.commit()

            return {"status": "success", "message": "Configuration updated successfully"}

        except Exception as e:
            logger.error(f"Error updating configuration: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error updating configuration: {str(e)}"
            )
