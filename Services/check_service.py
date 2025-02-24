from datetime import datetime
from uuid import uuid4
import logging
from database import get_db_connection

logger = logging.getLogger(__name__)


class CheckService:
    @staticmethod
    def create_check(transaction_id, check_number, amount, status, check_date, bank_name, bank_branch, bank_account,
                     swift_code):
        """Create a new check in the database."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                check_id = str(uuid4())
                now = datetime.now().isoformat()

                cursor.execute('''
                    INSERT INTO checks (
                        id, transaction_id, check_number, amount, status, 
                        check_date, bank_name, bank_branch, bank_account, 
                        swift_code, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    check_id, transaction_id, check_number, amount, status,
                    check_date, bank_name, bank_branch, bank_account,
                    swift_code, now, now
                ))

                return check_id

        except Exception as e:
            logger.error(f"Error creating check: {str(e)}")
            raise

    @staticmethod
    def update_check_status(check_id, status, updated_at=None):
        """Update the status of an existing check."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                if updated_at is None:
                    updated_at = datetime.now().isoformat()

                cursor.execute('''
                    UPDATE checks
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                ''', (status, updated_at, check_id))

                if cursor.rowcount == 0:
                    raise ValueError(f"Check with ID {check_id} not found")

                logger.info(f"Check {check_id} updated with status: {status}")

        except Exception as e:
            logger.error(f"Error updating check status: {str(e)}")
            raise

    @staticmethod
    def get_check_details(check_id):
        """Get detailed information about a specific check."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM checks WHERE id = ?
                ''', (check_id,))

                check = cursor.fetchone()
                if not check:
                    raise ValueError(f"Check with ID {check_id} not found")

                return dict(check)

        except Exception as e:
            logger.error(f"Error getting check details: {str(e)}")
            raise

    @staticmethod
    def get_checks_by_status(status):
        """Get all checks with a specific status."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM checks WHERE status = ?
                    ORDER BY created_at DESC
                ''', (status,))

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Error getting checks by status: {str(e)}")
            raise

    @staticmethod
    def get_checks_by_transaction(transaction_id):
        """Get all checks associated with a specific transaction."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM checks WHERE transaction_id = ?
                    ORDER BY created_at DESC
                ''', (transaction_id,))

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Error getting checks by transaction: {str(e)}")
            raise
