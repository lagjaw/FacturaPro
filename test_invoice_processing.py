import unittest
from invoice_processing import process_invoice_data

class TestInvoiceProcessing(unittest.TestCase):

    def test_process_invoice_data_with_valid_data(self):
        invoice_text = "Facture n° 12345\nTOTAL (1234.56)"
        expected_result = {
            "invoice_number": "12345",
            "total": "1234.56"
        }
        result = process_invoice_data(invoice_text)
        self.assertEqual(result, expected_result)

    def test_process_invoice_data_with_missing_number(self):
        invoice_text = "TOTAL (1234.56)"
        expected_result = {
            "invoice_number": None,
            "total": "1234.56"
        }
        result = process_invoice_data(invoice_text)
        self.assertEqual(result, expected_result)

    def test_process_invoice_data_with_missing_total(self):
        invoice_text = "Facture n° 12345"
        expected_result = {
            "invoice_number": "12345",
            "total": None
        }
        result = process_invoice_data(invoice_text)
        self.assertEqual(result, expected_result)

    def test_process_invoice_data_with_missing_data(self):
        invoice_text = "Aucune donnée"
        expected_result = {
            "invoice_number": None,
            "total": None
        }
        result = process_invoice_data(invoice_text)
        self.assertEqual(result, expected_result)

if __name__ == "__main__":
    unittest.main()
