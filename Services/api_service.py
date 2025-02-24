import requests
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class APIService:
    """Comprehensive API service for all endpoints"""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.timeout = 30

    def _handle_response(self, response: requests.Response) -> Dict:
        """Handle API response and errors"""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise

    # Invoice Processing Endpoints
    def upload_invoices(self, files: List) -> Dict:
        """Upload and process invoice files"""
        try:
            files_data = [("files", file) for file in files]
            response = self.session.post(
                f"{self.base_url}/process-invoice/",
                files=files_data,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            raise

    def search_invoices(self,
                        invoice_number: Optional[str] = None,
                        date_from: Optional[str] = None,
                        date_to: Optional[str] = None,
                        min_amount: Optional[float] = None,
                        max_amount: Optional[float] = None,
                        status: Optional[str] = None) -> Dict:
        """Search invoices with filters"""
        try:
            params = {
                "invoice_number": invoice_number,
                "date_from": date_from,
                "date_to": date_to,
                "min_amount": min_amount,
                "max_amount": max_amount,
                "status": status
            }
            params = {k: v for k, v in params.items() if v is not None}
            response = self.session.get(
                f"{self.base_url}/search-invoices/",
                params=params,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise

    def generate_bilan(self, date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict:
        """Generate financial report"""
        try:
            params = {
                "date_from": date_from,
                "date_to": date_to
            }
            params = {k: v for k, v in params.items() if v is not None}
            response = self.session.get(
                f"{self.base_url}/generate_bilan/",
                params=params,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Bilan generation failed: {str(e)}")
            raise

    # Payment Management Endpoints
    def divide_check(self, check_id: str, amounts: List[float]) -> Dict:
        """Divide a check into multiple amounts"""
        try:
            data = {
                "check_id": check_id,
                "amounts": amounts
            }
            response = self.session.post(
                f"{self.base_url}/payments/check/divide/",
                json=data,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Check division failed: {str(e)}")
            raise

    def replace_check(self, check_id: str, replacement_info: Dict) -> Dict:
        """Replace a bounced check"""
        try:
            response = self.session.post(
                f"{self.base_url}/payments/check/replace/{check_id}",
                json=replacement_info,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Check replacement failed: {str(e)}")
            raise

    def get_unpaid_checks(self) -> Dict:
        """Get list of unpaid checks"""
        try:
            response = self.session.get(
                f"{self.base_url}/payments/check/unpaid/",
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to get unpaid checks: {str(e)}")
            raise

    # Client Management Endpoints
    def get_clients(self) -> Dict:
        """Get list of all clients"""
        try:
            response = self.session.get(
                f"{self.base_url}/clients/",
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to get clients: {str(e)}")
            raise

    def get_client_details(self, client_id: str) -> Dict:
        """Get detailed information for a specific client"""
        try:
            response = self.session.get(
                f"{self.base_url}/clients/{client_id}",
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to get client details: {str(e)}")
            raise

    def get_key_accounts(self) -> Dict:
        """Get list of key account clients"""
        try:
            response = self.session.get(
                f"{self.base_url}/clients/key-accounts",
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to get key accounts: {str(e)}")
            raise

    # Stock Management Endpoints
    def get_stock_summary(self) -> Dict:
        """Get stock summary and alerts"""
        try:
            response = self.session.get(
                f"{self.base_url}/stock/summary/",
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to get stock summary: {str(e)}")
            raise

    def check_low_stock(self) -> Dict:
        """Check for low stock items"""
        try:
            response = self.session.get(
                f"{self.base_url}/stock/check/low-stock",
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to check low stock: {str(e)}")
            raise

    def check_expired_stock(self) -> Dict:
        """Check for expired items"""
        try:
            response = self.session.get(
                f"{self.base_url}/stock/check/expired",
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to check expired stock: {str(e)}")
            raise

    # Communication Endpoints
    def send_email(self, email_data: Dict) -> Dict:
        """Send email notification"""
        try:
            response = self.session.post(
                f"{self.base_url}/communications/email/send",
                json=email_data,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise

    def send_sms(self, sms_data: Dict) -> Dict:
        """Send SMS notification"""
        try:
            response = self.session.post(
                f"{self.base_url}/communications/sms/send",
                json=sms_data,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            raise

    # Transaction Endpoints
    def create_transaction(self, transaction_data: Dict) -> Dict:
        """Create a new transaction"""
        try:
            response = self.session.post(
                f"{self.base_url}/transactions/",
                json=transaction_data,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to create transaction: {str(e)}")
            raise

    def get_transaction(self, transaction_id: str) -> Dict:
        """Get transaction details"""
        try:
            response = self.session.get(
                f"{self.base_url}/transactions/{transaction_id}",
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to get transaction: {str(e)}")
            raise

    def get_client_transactions(self, client_id: str) -> Dict:
        """Get all transactions for a client"""
        try:
            response = self.session.get(
                f"{self.base_url}/transactions/client/{client_id}",
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to get client transactions: {str(e)}")
            raise
