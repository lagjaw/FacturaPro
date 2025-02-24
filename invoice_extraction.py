import pytesseract
from PIL import Image
import os
import re

# Fonction d'extraction du texte de la facture (image)
def extract_invoice_text(file_path):
    try:
        # Ouvrir l'image depuis le chemin du fichier
        image = Image.open(file_path)
        # Utiliser pytesseract pour extraire le texte
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        raise ValueError(f"Error during invoice extraction: {str(e)}")
