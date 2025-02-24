from unittest.mock import MagicMock
from Services.invoice_service import InvoiceService

def test_create_invoice():
    mock_db = MagicMock()
    invoice_service = InvoiceService(mock_db)

    client_id = "123"
    items = [{'product_id': '001', 'quantity': 2}]
    due_date = "2025-03-01"

    result = invoice_service.create_invoice(client_id, items, due_date)

    assert result is not None
    mock_db.commit.assert_called_once()
