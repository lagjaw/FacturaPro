from datetime import datetime
from uuid import uuid4
import logging
from database import get_db_connection

logger = logging.getLogger(__name__)

class CheckDivisionService:
    @staticmethod
    def create_check_division(check_id, amount, division_date, status):
        """Create a new check division in the database."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # First verify the check exists and get its amount
                cursor.execute('SELECT amount FROM checks WHERE id = ?', (check_id,))
                check = cursor.fetchone()
                if not check:
                    raise ValueError(f"Check with ID {check_id} not found")

                # Get existing divisions total
                cursor.execute('''
                    SELECT COALESCE(SUM(amount), 0) as total
                    FROM check_divisions
                    WHERE check_id = ?
                ''', (check_id,))
                current_total = cursor.fetchone()[0]

                # Verify the new division won't exceed check amount
                if current_total + amount > check['amount']:
                    raise ValueError(f"Division amount would exceed check amount. "
                                     f"Available: {check['amount'] - current_total}")

                division_id = str(uuid4())
                now = datetime.now().isoformat()

                cursor.execute('''
                    INSERT INTO check_divisions (
                        id, check_id, amount, division_date, 
                        status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    division_id, check_id, amount, division_date,
                    status, now, now
                ))

                return division_id

        except Exception as e:
            logger.error(f"Error creating check division: {str(e)}")
            raise

    @staticmethod
    def update_check_division_status(division_id, status, updated_at=None):
        """Update the status of an existing check division."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                if updated_at is None:
                    updated_at = datetime.now().isoformat()

                cursor.execute('''
                    UPDATE check_divisions
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                ''', (status, updated_at, division_id))

                if cursor.rowcount == 0:
                    raise ValueError(f"Check division with ID {division_id} not found")

                logger.info(f"Check Division {division_id} updated with status: {status}")

        except Exception as e:
            logger.error(f"Error updating check division status: {str(e)}")
            raise

    @staticmethod
    def get_divisions_by_check(check_id):
        """Get all divisions for a specific check."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT cd.*, c.check_number, c.amount as check_amount
                    FROM check_divisions cd
                    JOIN checks c ON cd.check_id = c.id
                    WHERE cd.check_id = ?
                    ORDER BY cd.created_at DESC
                ''', (check_id,))

                divisions = [dict(row) for row in cursor.fetchall()]

                if not divisions:
                    cursor.execute('SELECT * FROM checks WHERE id = ?', (check_id,))
                    if not cursor.fetchone():
                        raise ValueError(f"Check with ID {check_id} not found")

                return divisions

        except Exception as e:
            logger.error(f"Error getting divisions by check: {str(e)}")
            raise

    @staticmethod
    def get_divisions_by_status(status):
        """Get all divisions with a specific status."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT cd.*, c.check_number, c.amount as check_amount
                    FROM check_divisions cd
                    JOIN checks c ON cd.check_id = c.id
                    WHERE cd.status = ?
                    ORDER BY cd.created_at DESC
                ''', (status,))

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Error getting divisions by status: {str(e)}")
            raise

    @staticmethod
    def get_division_details(division_id):
        """Get detailed information about a specific check division."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT cd.*, c.check_number, c.amount as check_amount,
                           c.bank_name, c.bank_branch
                    FROM check_divisions cd
                    JOIN checks c ON cd.check_id = c.id
                    WHERE cd.id = ?
                ''', (division_id,))

                division = cursor.fetchone()
                if not division:
                    raise ValueError(f"Check division with ID {division_id} not found")

                return dict(division)

        except Exception as e:
            logger.error(f"Error getting division details: {str(e)}")
            raise

    @staticmethod
    def validate_division(check_id, amount, division_date):
        """Validate a potential check division before creating it."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Verify check exists and get its amount
                cursor.execute('SELECT amount, status FROM checks WHERE id = ?', (check_id,))
                check = cursor.fetchone()
                if not check:
                    raise ValueError(f"Check with ID {check_id} not found")

                if check['status'] not in ['pending', 'active']:
                    raise ValueError(f"Cannot divide check with status: {check['status']}")

                # Get existing divisions total
                cursor.execute('''
                    SELECT COALESCE(SUM(amount), 0) as total
                    FROM check_divisions
                    WHERE check_id = ?
                ''', (check_id,))
                current_total = cursor.fetchone()[0]

                available_amount = check['amount'] - current_total
                if amount > available_amount:
                    raise ValueError(f"Division amount ({amount}) exceeds available amount ({available_amount})")

                return {
                    "valid": True,
                    "check_amount": check['amount'],
                    "current_total_divisions": current_total,
                    "available_amount": available_amount,
                    "proposed_division": amount
                }

        except ValueError as e:
            return {
                "valid": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error validating division: {str(e)}")
            raise