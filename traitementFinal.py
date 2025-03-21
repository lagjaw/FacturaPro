from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import os
import hashlib
import re
import sqlite3
import json
import logging
import tempfile
import uuid
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
import uvicorn
import pytesseract
from PIL import Image, ImageFilter, ImageEnhance
from pdf2image import convert_from_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
)
logger = logging.getLogger(__name__)

API_URL = "http://127.0.0.1:8000"

class ImageProcessor:
    """Handles image processing for better OCR results."""

    @staticmethod
    def enhance_image(image: Image.Image) -> Image.Image:
        """Enhance image quality for better OCR recognition."""
        try:
            # Convert to grayscale if needed
            if image.mode != 'L':
                image = image.convert('L')

            # Apply adaptive thresholding
            img_array = np.array(image)
            blurred = cv2.GaussianBlur(img_array, (5, 5), 0)
            binary = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )

            # Noise reduction
            denoised = cv2.fastNlMeansDenoising(binary)

            # Convert back to PIL Image
            enhanced_image = Image.fromarray(denoised)

            # Increase contrast
            enhancer = ImageEnhance.Contrast(enhanced_image)
            enhanced_image = enhancer.enhance(2.0)

            # Sharpen
            enhanced_image = enhanced_image.filter(ImageFilter.SHARPEN)

            return enhanced_image
        except Exception as e:
            logger.error(f"Error in image enhancement: {str(e)}")
            return image

    @staticmethod
    def deskew_image(image: Image.Image) -> Image.Image:
        """Correct image skew for better OCR accuracy."""
        try:
            # Convert to numpy array
            img_array = np.array(image)

            # Apply edge detection
            edges = cv2.Canny(img_array, 50, 150, apertureSize=3)

            # Find lines using probabilistic Hough transform
            lines = cv2.HoughLinesP(
                edges, 1, np.pi / 180, 100,
                minLineLength=100, maxLineGap=10
            )

            if lines is not None and len(lines) > 0:
                angles = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if x2 - x1 != 0:
                        angle = np.arctan((y2 - y1) / (x2 - x1)) * 180 / np.pi
                        angles.append(angle)

                median_angle = np.median(angles)

                if abs(median_angle) > 0.5:
                    height, width = img_array.shape
                    center = (width // 2, height // 2)
                    rotation_matrix = cv2.getRotationMatrix2D(
                        center, median_angle, 1.0
                    )
                    rotated = cv2.warpAffine(
                        img_array, rotation_matrix, (width, height),
                        flags=cv2.INTER_CUBIC,
                        borderMode=cv2.BORDER_REPLICATE
                    )
                    return Image.fromarray(rotated)

            return image
        except Exception as e:
            logger.error(f"Error in image deskewing: {str(e)}")
            return image


class DatabaseManager:
    """Manages database operations for the invoice processing system."""

    def __init__(self, db_path: str = "invoices.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Creates and returns a database connection."""
        return sqlite3.connect(self.db_path)

    def init_db(self) -> None:
        """Initializes the database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''CREATE TABLE IF NOT EXISTS clients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                address TEXT,
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )''')


            # Create invoices table with exact schema
            cursor.execute('''CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                client_id Text NOT NULL,
                invoice_number TEXT NOT NULL,
                date DATETIME DEFAULT CURRENT_TIMESTAMP,
                due_date DATETIME,
                bill_to TEXT,
                total NUMERIC DEFAULT 0,
                subtotal NUMERIC DEFAULT 0,
                tax NUMERIC DEFAULT 0,
                gstin TEXT,
                discount NUMERIC DEFAULT 0,
                bank_name TEXT,
                branch_name TEXT,
                bank_account_number TEXT,
                bank_swift_code TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                items TEXT,
                FOREIGN KEY (client_id) REFERENCES clients (id) 
            )''')

            # Create invalid_invoices table with exact schema
            cursor.execute('''CREATE TABLE IF NOT EXISTS invalid_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT,
                date TEXT,
                due_date TEXT,
                bill_to TEXT,
                total REAL,
                subtotal REAL,
                tax REAL,
                gstin TEXT,
                discount REAL,
                bank_name TEXT,
                branch_name TEXT,
                bank_account_number TEXT,
                bank_swift_code TEXT,
                status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                items TEXT,
                error_message TEXT
            )''')

            conn.commit()

    def get_client_by_email(self, email:str ) -> Optional[dict]:
        """recherche d'un client par son email"""

        with self.get_connection() as conn :
            cursor = conn.cursor()
            cursor.execute("SELECT id , name , email , phone From clients where email=?",(email,))
            result =cursor.fetchone()

            return dict(zip(['id','name','email','phone'],result)) if result else None 
        
    def get_client_by_phone(self, phone: str) -> Optional[dict]:
        """Recherche un client par son numéro de téléphone."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email, phone FROM clients WHERE phone = ?", (phone,))
            result = cursor.fetchone()
            return dict(zip(['id', 'name', 'email', 'phone'], result)) if result else None
        
    

    def create_client(self, client_data: dict) -> str:

        with self.get_connection() as conn: 
            cursor = conn.cursor()
            client_id = str(uuid.uuid4())

            cursor.execute('''INSERT INTO clients (id, name, email, phone, address) VALUES (?, ?, ?, ?, ?)''', (
                client_id,
                client_data.get('name'),
                client_data.get('email'),
                client_data.get('phone'),  # Corrected: removed the space
                client_data.get('address')
            ))

            conn.commit()
            return client_id


class EnhancedInvoiceProcessor:
    """Advanced invoice processing with improved extraction and validation."""

    def __init__(self, temp_dir: str = "temp"):
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
        self.image_processor = ImageProcessor()
        self.db_manager = DatabaseManager()

    def _extract_text(self, file_path: str, file_ext: str) -> str:
        """Extract text from PDF or image files with enhanced OCR."""
        try:
            if file_ext.lower() == '.pdf':
                images = convert_from_path(file_path, dpi=300)
                return "\n".join([self._process_single_image(img) for img in images])
            else:
                return self._process_single_image(Image.open(file_path))
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            raise

    def _process_single_image(self, image: Image.Image) -> str:
        """Process single image with enhanced OCR settings."""
        try:
            # Apply image enhancements
            image = self.image_processor.enhance_image(image)
            image = self.image_processor.deskew_image(image)

            # OCR with improved settings
            custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
            return pytesseract.image_to_string(image, config=custom_config)
        except Exception as e:
            logger.error(f"Error in OCR processing: {str(e)}")
            raise

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better extraction."""
        # Convert to lowercase
        text = text.lower()

        # Normalize unicode characters
        text = text.replace('–', '-').replace('—', '-')
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)

        # Normalize date separators
        text = re.sub(r'(\d)\s+(\d)', r'\1\2', text)

        return text.strip()

    def _extract_invoice_details(self, text: str) -> Dict[str, Any]:
        # Normalize text
        text = re.sub(r'\s+', ' ', text.strip())

        # Extract PO Number with multiple formats
        invoice_patterns = [
            r'PO Number[:\s]*([^\s]+)',  # Original pattern
            r'PO\s*Number\s*:?\s*(\d+)',  # PO Number:51
            r'INVOICE\s*(?:ID|#)\s*(?:INV/)?([0-9/-]+)',  # INVOICE ID INV/20-11/338
            r'invoice\s*number\s*([A-Z0-9-]+)',  # invoice number 6508-985
            r'INVOICE\s*#\s*(\d+(?:-\d+)?)',  # INVOICE # 6508-985
            r'Invoice\s*number\s*:\s*([A-Z0-9-]+)',  # Invoice number: ABC-123
            r'PO Number[:\s]*([^\s]+)',  # Original pattern
            r'PO\s*Number\s*:?\s*(\d+)',  # PO Number:51
            r'INVOICE\s*(?:ID|#)\s*(?:INV/)?([0-9/-]+)',  # INVOICE ID INV/20-11/338
            r'invoice\s*number\s*([A-Z0-9-]+)',  # invoice number 6508-985
            r'INVOICE\s*#\s*(\d+(?:-\d+)?)',  # INVOICE # 6508-985
            r'Invoice\s*number\s*:\s*([A-Z0-9-]+)'  # Invoice number: ABC-123
        ]

        invoice_number = None
        for pattern in invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_number = match.group(1)
                break

        # Date extraction with multiple formats
        date_patterns = [
            r'(?:Invoice\s+)?Date\s*:?\s*(\d{1,2}[-/.][A-Za-z]{3}[-/.]\d{4})',  # 19-Feb-1993
            r'Date\s*:?\s*(\d{1,2}[-/.][A-Za-z]{3}[-/.]\d{4})',  # Date: 19-Feb-1993
            r'Date\s*:?\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{4})',  # Date: 19/02/1993
            r'Date\s*:?\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})',  # Date: 1993/02/19
            r'Invoice\s+Date\s*:?\s*(\d{1,2}[-/.][A-Za-z]{3}[-/.]\d{4})',  # Invoice Date: 19-Feb-1993
            r'Date[:\s]*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})',  # Original pattern
            r'(?:Invoice\s+)?Date\s*:?\s*(\d{2}-[A-Za-z]{3}-\d{4})',  # 19-Feb-1993
            r'Date\s*:?\s*(\d{1,2}[-/.][A-Za-z]{3}[-/.]\d{4})',  # Date: 19-Feb-1993
            r'Date\s*:?\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{4})',  # Date: 19/02/1993
            r'Date\s*:?\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})',  # Date: 1993/02/19
            r'Date[:\s]*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})'
        ]

        invoice_date = None
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_date = match.group(1)
                break

        # Due Date extraction
        due_date_patterns = [
            r'Due\s+Date\s*:?\s*(\d{2}-[A-Za-z]{3}-\d{4})',  # 16-Oct-2016
            r'Due\s+Date\s*:?\s*(\d{2}/\d{2}/\d{4})',  # DD/MM/YYYY
            r'Due\s+Date\s*:?\s*(\d{2}\.\d{2}\.\d{4})',  # DD.MM.YYYY
            r'Due Date[:\s]*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})',  # Original pattern
            r'Due\s+Date\s*:?\s*(\d{2}-[A-Za-z]{3}-\d{4})',  # Due Date: 28-Dec-1994
            r'Due\s+Date\s*:?\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{4})',  # Due Date: 28/12/1994
            r'Due\s+Date\s*:?\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})',  # Due Date: 1994/12/28
            r'Due Date[:\s]*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})'
        ]

        due_date = None
        for pattern in due_date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                due_date = match.group(1)
                break

        # Amount extraction with multiple formats
        total_patterns = [
            r'TOTAL\s*:?\s*(\d+\.?\d*)\s*(?:EUR|USD|\$)',  # TOTAL: 734.33 EUR
            r'TOTAL\s*:?\s*(\d+,\d{2})\s*(?:EUR|USD|\$)',  # TOTAL: 734,33 EUR
            r'TOTAL\s*:?\s*(?:EUR|USD|\$)\s*(\d+\.?\d*)',  # TOTAL: $ 734.33
            r'TOTAL\s*:?\s*(?:EUR|USD|\$)\s*(\d+,\d{2})',  # TOTAL: $ 734,33
            r'TOTAL\s*:?\s*(\d+\.?\d*)',  # TOTAL: 734.33
            r'TOTAL\s*:?\s*(\d+)',  # TOTAL: 734
            r'Total\s*:?\s*(\d+\.?\d*)',  # Total: 734.33
            r'Total\s*:?\s*(\d+\.?\d*)\s*(?:EUR|USD|\$)',  # Total: 734.33 $
            r'TOTAL\s*:\s*(\d+\.?\d*)\s*\$',  # TOTAL: 734.33 $
            r'Total\s+in\s+words[^:]*?:\s*[^:]*?:\s*(\d+\.?\d*)',  # Total in words...: 734.33
            r'TOTAL\s*:\s*(?:EUR|USD|\$)?\s*(\d+[.,]\d{2})',  # TOTAL: EUR 734,33
            r'Total\s*Amount\s*:?\s*(\d+\.?\d*)',  # Total Amount: 734.33
            r'Amount\s+Due\s*:?\s*(\d+\.?\d*)',  # Amount Due: 734.33
            r'TOTAL[:\s]*\$?([0-9,]+\.[0-9]{2})'

        ]

        total = None
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    total = float(match.group(1).replace(',', '.'))
                    break
                except ValueError:
                    continue

        # Subtotal extraction
        subtotal_patterns = [
            r'SUB[_\s]?TOTAL\s*:\s*(\d+\.?\d*)\s*(?:EUR|USD|\$)',  # SUB_TOTAL: 725.30 EUR
            r'SUB[_\s]?TOTAL\s*:\s*(\d+,\d{2})\s*(?:EUR|USD|\$)',  # SUB_TOTAL: 725,30 EUR
            r'SUB[_\s]?TOTAL\s*:\s*(\d+\.?\d*)'  # SUB_TOTAL: 725.30
            r'SUB[_\s]?TOTAL\s*:?\s*(?:EUR|USD|\$)?\s*(\d+[.,]\d{2})',  # SUB_TOTAL: EUR 725,30
            r'Net\s+Amount\s*:?\s*(\d+\.?\d*)',  # Net Amount: 725.30
            r'Sub\s*Total\s*:?\s*(\d+\.?\d*)',  # Sub Total: 725.30
            r'Subtotal\s*Amount\s*:?\s*(\d+\.?\d*)',  # Subtotal Amount: 725.30
            r'SUB_TOTAL[:\s]*\$?([0-9,]+\.[0-9]{2})'

        ]

        subtotal = None
        for pattern in subtotal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    subtotal = float(match.group(1).replace(',', '.'))
                    break
                except ValueError:
                    continue

        # Tax extraction with percentage
        tax_patterns = [
            r'TAX:?\s*VAT\s*\((\d+\.?\d*)%\)\s*:?\s*(\d+\.?\d*)',  # TAX:VAT (3.89%): 28.18
            r'TAX:?\s*VAT\s*:?\s*(\d+\.?\d*)',  # TAX:VAT: 28.18
            r'GST\(%\)\s*:?\s*(\d+\.?\d*)'  # GST(%): 28.18
            r'TAX:?\s*\((\d+\.?\d*)%\)\s*:?\s*(\d+\.?\d*)',  # TAX:(3.89%): 28.18
            r'VAT\s*\((\d+\.?\d*)%\)\s*:?\s*(\d+\.?\d*)',  # VAT(3.89%): 28.18
            r'Tax\s*Amount\s*:?\s*(\d+\.?\d*)',  # Tax Amount: 28.18
            r'GST\s*\((\d+)%\)\s*:?\s*(\d+\.?\d*)',  # GST(7%): 28.18
            r'TAX:?\s*VAT\s*:?\s*(\d+\.?\d*)\s*(?:EUR|USD|\$)',  # TAX:VAT: 28.18 EUR
            r'TAX[:\s]*[^\d]*\$?([0-9,]+\.[0-9]{2})'

        ]

        tax = None
        tax_percentage = None
        for pattern in tax_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) > 1:
                    tax_percentage = float(match.group(1))
                    tax = float(match.group(2))
                else:
                    tax = float(match.group(1))
                break

        # Discount extraction
        discount_patterns = [
            r'DISCOUNT\s*\((\d+\.?\d*)%\)\s*:?\s*\(?\s*(\d+\.?\d*)\s*(?:EUR|USD|\$)?\)?',
            r'DISCOUNT\s*\((\d+\.?\d*)%\)\s*:?\s*(\d+\.?\d*)',
            r'DISCOUNT[:\s]*[^\d]*\$?([0-9,]+\.[0-9]{2})'
        ]

        discount = None
        discount_percentage = None
        for pattern in discount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                discount_percentage = float(match.group(1))
                discount = float(match.group(2))
                break

        # Bill to/Buyer information
        buyer_patterns = [
            r'Bill\s+to\s*:?\s*([^:\n]+?)(?=\s+\d{5}|\s+Email|Tel|GSTIN|$)',
            r'Buyer\s*:?\s*([^:\n]+?)(?=\s+\d{5}|\s+Email|Tel|GSTIN|$)',
            r'Bill\s+to\s*:?\s*([^:\n]+?)(?=\s+(?:\d{1,5}|Email|Tel|GSTIN|$))',
            r'Bill\s+to\s*:?\s*([^\n]+?)(?=\s+Tel:)',
            r'Bill\s+to\s*:?\s*([^\n]+?)(?=\s+Email:)',
            r'Bill\s+to\s*:?\s*([^\n]+?)(?=\s+Site:)',
            r'Bill to[:\s]*([^0-9]+)'
        ]

        buyer_info = None
        for pattern in buyer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                buyer_info = match.group(1).strip()
                break

        # Bank details
        bank_name_pattern = r'(?:State|Central)\s+Bank\s+of\s+([A-Za-z]+)'
        branch_name_pattern = r'Branch\s+Name\s+([^(]+?)(?=\s+(?:Bank|Account|Swift|\(|$))'
        account_number_pattern = r'Bank\s+Account\s+Number\s+(\d+)'
        swift_code_pattern = r'Bank\s+Swift\s+Code\s+([A-Z0-9]+)'

        bank_name_match = re.search(bank_name_pattern, text, re.IGNORECASE)
        branch_name_match = re.search(branch_name_pattern, text, re.IGNORECASE)
        account_number_match = re.search(account_number_pattern, text, re.IGNORECASE)
        swift_code_match = re.search(swift_code_pattern, text, re.IGNORECASE)

        # GSTIN extraction
        gstin_match = re.search(r'(?:GSTIN|OG@AAMFCO376K124)\s*:?\s*([0-9A-Z@]+)', text)

        #ITEMS
        items = []
        item_pattern = r'(?P<ITEMS>[\w\s]+)\n(?P<QUANTITY>[0-9.]+)\n(?P<PRICE>[$€]?[0-9,.]+)'

        items_match = re.finditer(item_pattern, text)
        for match in items_match:
            try:
                price_str = match.group('PRICE').replace('$', '').replace('€', '').replace(',', '')
                item_dict = {
                    "ITEMS": match.group('ITEMS').strip(),
                    "QUANTITY": float(match.group('QUANTITY')),
                    "PRICE": float(price_str)
                }
                items.append(item_dict)
            except (ValueError, AttributeError) as e:
                continue

        # Currency detection
        currency = 'EUR'  # Default currency
        if re.search(r'\$|USD', text):
            currency = 'USD'


        
        email_match = re.search(r'Email[:\s]*([\w.-]+@[\w.-]+\.\w+)', text, re.IGNORECASE)
        phone_match = re.search(r'(?:Tel|Phone)[:\s]*([+\d\s-]{8,})', text, re.IGNORECASE)
        address_match = re.search(r'Address[:\s]*(.*?)(?=\n\s*(?:GSTIN|Phone|Email))', text, re.IGNORECASE | re.DOTALL)


        client_data = {
            'name' : buyer_info,
            'email' : email_match.group(1).strip() if email_match else None, 
            'phone' : phone_match.group(1).strip() if phone_match else None,
            'address': address_match.group(1).strip() if address_match else None 
        }


        # Construct invoice data
        invoice_data = {
            'invoice_number': invoice_number,
            'date': invoice_date,
            'due_date': due_date,
            'bill_to': buyer_info,
            'total': total,
            'subtotal': subtotal,
            'tax_percentage': tax_percentage,
            'tax': tax,
            'discount_percentage': discount_percentage,
            'discount': discount,
            'currency': currency,
            'gstin': gstin_match.group(1) if gstin_match else None,
            'bank_name': bank_name_match.group(0) if bank_name_match else None,
            'branch_name': branch_name_match.group(1).strip() if branch_name_match else None,
            'account_number': account_number_match.group(1) if account_number_match else None,
            'bank_swift_code': swift_code_match.group(1) if swift_code_match else None,
            'client' : client_data,
            "items": str(items)
        }

        return invoice_data

    def save_invalid_invoice(self, data: Dict[str, Any], error_message: str) -> None:
        """Save invalid invoice to database with error message."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO invalid_invoices (
                        invoice_number, date, due_date, bill_to, total, 
                        subtotal, tax, gstin, discount, bank_name, branch_name,
                        bank_account_number, bank_swift_code, status, items,
                        error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data.get('invoice_number'),
                    data.get('date'),
                    data.get('due_date'),
                    data.get('bill_to'),
                    data.get('total'),
                    data.get('subtotal'),
                    data.get('tax'),
                    data.get('gstin'),
                    data.get('discount'),
                    data.get('bank_name'),
                    data.get('branch_name'),
                    data.get('bank_account_number'),
                    data.get('bank_swift_code'),
                    'invalid',
                    json.dumps(data.get('items', [])),
                    error_message
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving invalid invoice: {str(e)}")

    def process_invoice(self, text: str) -> Dict[str, Any]:
        """Process invoice text and extract structured data with validation for total field."""
        try:
            # Extract invoice details
            invoice_data = self._extract_invoice_details(text)
            client_data = invoice_data.get('client')

            client_id = self._handle_client_processing(client_data)

            # Check if total exists and is valid
            if invoice_data.get('currency') is None:
                # Save to invalid_invoices if total is missing
                self.save_invalid_invoice(invoice_data, "Missing required field: currency")
                return {
                    "status": "error",
                    "error": "Missing required field: currency",
                    "data": invoice_data
                }
            
            

            # If total exists, try to save directly to invoices table
            try:
                # Generate unique ID
                invoice_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()
                if invoice_data.get('invoice_number'):
                    invoice_id = hashlib.md5(invoice_data['invoice_number'].encode()).hexdigest()

                # Set default values for required fields if they're missing
                invoice_data['date'] = invoice_data.get('date') or datetime.now().strftime('%Y-%m-%d')
                invoice_data['due_date'] = invoice_data.get('due_date') or invoice_data['date']
                invoice_data['bill_to'] = invoice_data.get('bill_to') or 'Not found'
                invoice_data['invoice_number'] = invoice_data.get('invoice_number') or f'INV-{invoice_id[:8]}'

                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO invoices (
                            id, invoice_number, date, due_date, bill_to, total, 
                            subtotal, tax, gstin, discount, bank_name, branch_name,
                            bank_account_number, bank_swift_code, status, items,client_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)
                    ''', (
                        invoice_id,
                        invoice_data['invoice_number'],
                        invoice_data['date'],
                        invoice_data['due_date'],
                        invoice_data['bill_to'],
                        invoice_data['total'],
                        invoice_data.get('subtotal', invoice_data['total']),  # Use total if subtotal missing
                        invoice_data.get('tax', 0),  # Default tax to 0
                        invoice_data.get('gstin'),
                        invoice_data.get('discount', 0),  # Default discount to 0
                        invoice_data.get('bank_name'),
                        invoice_data.get('branch_name'),
                        invoice_data.get('account_number'),
                        invoice_data.get('bank_swift_code'),
                        'pending',
                        json.dumps(invoice_data.get('items', [])),
                        client_id
                    ))
                    conn.commit()

                    return {
                        "status": "success",
                        "data": invoice_data
                    }

            except Exception as e:
                logger.error(f"Error saving valid invoice: {str(e)}")
                # If saving fails, save to invalid_invoices
                self.save_invalid_invoice(invoice_data, f"Failed to save invoice: {str(e)}")
                return {
                    "status": "error",
                    "error": "Failed to save invoice",
                    "data": invoice_data
                }

        except Exception as e:
            error_message = str(e)
            # Save to invalid_invoices if any error occurs
            self.save_invalid_invoice({}, error_message)
            return {
                "status": "error",
                "error": error_message
            }
        
    def _handle_client_processing(self, client_data: dict) -> str:
        """ Gere les verifications et l'insertion du client """
        try : 
            # Verfier si le client eciste par email
            if client_data.get('email'):
                existing_client = self.db_manager.get_client_by_email(client_data['email'])
                if existing_client:
                    return existing_client['id']
                
            if client_data.get('phone'):
                existing_client = self.db_manager.get_client_by_phone(client_data['phone'])
                if existing_client:
                    return existing_client['id']
                
            # Si aucun client trouve , en creer un nouveau 
            return self.db_manager.create_client({
                'name' : client_data.get('name', 'Unknown Client'),
                'email' : client_data.get('email'),
                'phone' : client_data.get('phone'),
                'address': client_data.get('address')
            })
        
        except Exception as e :
            logger.error(f"Error processing client: {str(e)}")
            return self.db_manager.create_client({
                'name' : 'Unknown Client',
                'email' : 'unknown@gmail.com',
            })


    async def process_files(self, files: List[UploadFile]) -> List[Dict[str, Any]]:
        """Process multiple invoice files."""
        results = []
        for file in files:
            temp_file = None
            try:
                logger.info(f"Processing invoice: {file.filename}")

                # Validate file extension
                file_ext = os.path.splitext(file.filename)[1].lower()
                if file_ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
                    raise ValueError(f"Unsupported file format: {file_ext}")

                # Create temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
                content = await file.read()
                temp_file.write(content)
                temp_file.close()

                # Process file
                text = self._extract_text(temp_file.name, file_ext)
                result = self.process_invoice(text)
                result["filename"] = file.filename
                results.append(result)

            except Exception as e:
                logger.error(f"Error processing {file.filename}: {str(e)}")
                results.append({
                    "status": "error",
                    "filename": file.filename,
                    "error": str(e)
                })
            finally:
                if temp_file and os.path.exists(temp_file.name):
                    try:
                        os.unlink(temp_file.name)
                    except Exception as e:
                        logger.error(f"Error deleting temporary file: {str(e)}")

        return results


# FastAPI application
app = FastAPI(
    title="Enhanced Invoice Processing API",
    description="API for processing and managing invoices",
    version="2.0.0"
)


@app.post("/process-invoice/")
async def process_invoice_endpoint(files: List[UploadFile] = File(...)):
    """Process invoice files with enhanced validation and error handling."""
    processor = EnhancedInvoiceProcessor()
    results = await processor.process_files(files)

    return {
        "status": "success",
        "processed": len(files),
        "results": results
    }

@app.get("/search-invoices/")  # Changed to match frontend URL
async def search_invoices(
        invoice_number: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        status: Optional[str] = None
):
    """Search invoices with various filters."""
    try:
        with DatabaseManager().get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM invoices WHERE 1=1"
            params = []

            if invoice_number:
                # Use exact match instead of LIKE
                query += " AND invoice_number = ?"
                params.append(invoice_number)

            if date_from:
                query += " AND date >= ?"
                params.append(date_from)

            if date_to:
                query += " AND date <= ?"
                params.append(date_to)

            if min_amount:
                query += " AND total >= ?"
                params.append(min_amount)

            if max_amount:
                query += " AND total <= ?"
                params.append(max_amount)

            if status:
                query += " AND status = ?"
                params.append(status)

            # Debug logging
            logger.info(f"Search Query: {query}")
            logger.info(f"Search Params: {params}")

            cursor.execute(query, params)
            results = cursor.fetchall()

            columns = [description[0] for description in cursor.description]
            invoices = []

            for row in results:
                invoice = dict(zip(columns, row))
                invoice['items'] = json.loads(invoice['items']) if invoice['items'] else []
                invoices.append(invoice)

            return {
                "invoices": invoices,
                "count": len(invoices)
            }

    except Exception as e:
        logger.error(f"Error searching invoices: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching invoices: {str(e)}"
        )


@app.get("/generate_bilan/")
async def generate_bilan(date_from: str = None, date_to: str = None):
    """Generate financial report for invoices."""
    try:
        with DatabaseManager().get_connection() as conn:
            cursor = conn.cursor()

            # Query for valid invoices statistics
            query = """
            SELECT 
                COUNT(*) as total_invoices,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_invoices,
                SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid_invoices,
                SUM(total) as total_amount,
                SUM(subtotal) as total_subtotal,
                SUM(tax) as total_tax,
                SUM(discount) as total_discount,
                MIN(total) as min_amount,
                MAX(total) as max_amount,
                AVG(total) as avg_amount
            FROM invoices
            WHERE 1=1
            """
            params = []

            if date_from:
                query += " AND date >= ?"
                params.append(date_from)

            if date_to:
                query += " AND date <= ?"
                params.append(date_to)

            cursor.execute(query, params)
            result = cursor.fetchone()

            # Query for invalid invoices statistics
            invalid_query = """
            SELECT COUNT(*) as total_invalid,
                   COUNT(DISTINCT error_message) as unique_errors
            FROM invalid_invoices
            WHERE 1=1
            """

            if date_from:
                invalid_query += " AND date >= ?"
            if date_to:
                invalid_query += " AND date <= ?"

            cursor.execute(invalid_query, params)
            invalid_result = cursor.fetchone()

            # Query for common errors
            error_query = """
            SELECT error_message, COUNT(*) as count
            FROM invalid_invoices
            WHERE 1=1
            """
            if date_from:
                error_query += " AND date >= ?"
            if date_to:
                error_query += " AND date <= ?"

            error_query += " GROUP BY error_message ORDER BY count DESC LIMIT 5"

            cursor.execute(error_query, params)
            common_errors = cursor.fetchall()

            # Construct the bilan
            bilan = {
                "période": {
                    "du": date_from if date_from else "début",
                    "au": date_to if date_to else "aujourd'hui"
                },
                "statistiques_factures": {
                    "total_factures": result[0],
                    "factures_en_attente": result[1],
                    "factures_payées": result[2],
                    "montant_total": round(result[3], 2) if result[3] else 0,
                    "total_ht": round(result[4], 2) if result[4] else 0,
                    "total_tva": round(result[5], 2) if result[5] else 0,
                    "total_remises": round(result[6], 2) if result[6] else 0,
                    "montant_minimum": round(result[7], 2) if result[7] else 0,
                    "montant_maximum": round(result[8], 2) if result[8] else 0,
                    "montant_moyen": round(result[9], 2) if result[9] else 0
                },
                "statistiques_erreurs": {
                    "total_factures_invalides": invalid_result[0],
                    "types_erreurs_uniques": invalid_result[1],
                    "erreurs_fréquentes": [
                        {"message": error[0], "occurrences": error[1]}
                        for error in common_errors
                    ]
                }
            }

            return bilan

    except Exception as e:
        logger.error(f"Error generating bilan: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating bilan: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
