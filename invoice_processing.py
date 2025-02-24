import os
import pandas as pd
import pytesseract
import re
from PIL import Image
import json

# Path to the directory containing invoice images
invoice_image_directory = "dataset/train/Template1_Instance6.jpg"

# Function to process invoice data for accounting
def process_invoice_for_accounting(invoice_image_path):
    img = Image.open(invoice_image_path)
    invoice_text = pytesseract.image_to_string(img)

    # Normalisation du texte
    invoice_text = re.sub(r'\s+', ' ', invoice_text)

    # Extraction des données avec des regex
    invoice_number = re.search(r'PO Number[:\s]*([^\s]+)', invoice_text)
    date = re.search(r'Date[:\s]*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', invoice_text)
    due_date = re.search(r'Due Date[:\s]*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', invoice_text)
    bill_to = re.search(r'Bill to[:\s]*([^0-9]+)', invoice_text)
    total = re.search(r'TOTAL[:\s]*\$?([0-9,]+\.[0-9]{2})', invoice_text)
    subtotal = re.search(r'SUB_TOTAL[:\s]*\$?([0-9,]+\.[0-9]{2})', invoice_text)
    tax = re.search(r'TAX[:\s]*[^\d]*\$?([0-9,]+\.[0-9]{2})', invoice_text)
    discount = re.search(r'DISCOUNT[:\s]*[^\d]*\$?([0-9,]+\.[0-9]{2})', invoice_text)

    gstin = re.search(r'GSTIN[:\s]*([A-Z0-9@]+)', invoice_text)

    # Création d'un dictionnaire avec les données extraites
    processed_invoice = {
        "invoice_number": invoice_number.group(1) if invoice_number else "Not found",
        "date": date.group(1) if date else "Not found",
        "due_date": due_date.group(1) if due_date else "Not found",
        "bill_to": bill_to.group(1).strip() if bill_to else "Not found",
        "total": float(total.group(1).replace(',', '')) if total else 0.0,
        "subtotal": float(subtotal.group(1).replace(',', '')) if subtotal else 0.0,
        "tax": float(tax.group(1).replace(',', '')) if tax else 0.0,
        "gstin": gstin.group(1) if gstin else "Not found",
        "discount": discount.group(1)if discount else "Not found"
    }

    return processed_invoice


# Function to generate the JSON response for accounting entries
def generate_accounting_response(invoice_image_path):
        invoices_data = []

        # Loop through all image files in the specified directory
        for filename in os.listdir(invoice_image_path):
            if filename.lower().endswith(('.bmp', '.gif', '.jpeg', '.jpg', '.png')):
                invoice_path = os.path.join(invoice_image_path, filename)
                processed_invoice = process_invoice_for_accounting(invoice_path)
                invoices_data.append(processed_invoice)

        # Create a DataFrame from the invoices data
        df = pd.DataFrame(invoices_data)

        # Generate summary statistics
        total_summary = df[['total', 'subtotal', 'tax']].sum().to_dict()
        total_summary['total_invoices'] = df.shape[0]

        # Convert the DataFrame to a JSON report
        report = {
            "invoices": invoices_data,
            "summary": total_summary
        }

        return report

# Main function to process all images in the dataset
def process_all_invoices(directory):
    results = {}
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):  # Check for image file extensions
            image_path = os.path.join(directory, filename)
            results[filename] = generate_accounting_response(image_path)

    return results

if __name__ == "__main__":
    invoice_directory = "dataset/train/"  # Change this to your directory containing invoices
    report = generate_accounting_response(invoice_directory)

    # Print the report
    print(json.dumps(report, indent=4))
