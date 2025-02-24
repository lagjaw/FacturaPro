import re
from typing import Optional, Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinalAmountExtractor:
    """Extracteur final de montants avec validation stricte."""

    # Patterns pour les montants
    AMOUNT_PATTERN = r'(?:[\d\s,.]+)'
    CURRENCY = r'(?:EUR|€)?'

    # Patterns pour identifier les montants avec leur contexte
    PATTERNS = {
        'ttc': [
            # Montants TTC explicites
            rf'Total\s*(?:TTC|TVA\s*incluse)\s*:?\s*{CURRENCY}\s*({AMOUNT_PATTERN})',
            rf'Montant\s*TTC\s*:?\s*{CURRENCY}\s*({AMOUNT_PATTERN})',
            rf'TTC\s*:?\s*{CURRENCY}\s*({AMOUNT_PATTERN})',
            rf'{CURRENCY}\s*({AMOUNT_PATTERN})\s*TTC',
        ],
        'ht': [
            # Montants HT explicites
            rf'(?:Total|Montant)\s*HT\s*:?\s*{CURRENCY}\s*({AMOUNT_PATTERN})',
            rf'HT\s*:?\s*{CURRENCY}\s*({AMOUNT_PATTERN})',
            rf'{CURRENCY}\s*({AMOUNT_PATTERN})\s*HT',
            rf'Hors\s*taxe\s*:?\s*{CURRENCY}\s*({AMOUNT_PATTERN})',
            rf'Base\s*(?:HT)?\s*:?\s*{CURRENCY}\s*({AMOUNT_PATTERN})',
            rf'Base\s*imposable\s*:?\s*{CURRENCY}\s*({AMOUNT_PATTERN})',
        ],
        'total': [
            # Montants totaux sans précision HT/TTC
            rf'Total\s*:?\s*{CURRENCY}\s*({AMOUNT_PATTERN})',
            rf'Total\s*à\s*payer\s*:?\s*{CURRENCY}\s*({AMOUNT_PATTERN})',
            rf'À\s*payer\s*:?\s*{CURRENCY}\s*({AMOUNT_PATTERN})',
            rf'Montant\s*total\s*:?\s*{CURRENCY}\s*({AMOUNT_PATTERN})',
        ],
        'tax': [
            # TVA
            rf'TVA\s*(?:\d+%?)?\s*:?\s*{CURRENCY}\s*({AMOUNT_PATTERN})',
            rf'T\.?V\.?A\.?\s*:?\s*{CURRENCY}\s*({AMOUNT_PATTERN})',
        ],
        'tax_rate': [
            r'TVA\s*\(?(\d+)%\)?',
            r'Taux\s*(?:de)?\s*TVA\s*:?\s*(\d+)%',
        ]
    }

    @staticmethod
    def clean_amount(amount_str: str) -> Optional[float]:
        """Nettoie et normalise un montant."""
        try:
            # Supprimer les caractères non numériques sauf , et .
            amount_str = re.sub(r'[^\d,.-]', '', amount_str)

            # Gérer les différents formats de séparateurs
            if ',' in amount_str and '.' in amount_str:
                last_dot = amount_str.rindex('.')
                last_comma = amount_str.rindex(',')
                if last_dot > last_comma:
                    amount_str = amount_str.replace(',', '')
                else:
                    amount_str = amount_str.replace('.', '').replace(',', '.')
            elif ',' in amount_str:
                amount_str = amount_str.replace(',', '.')

            amount = float(amount_str)
            return round(amount, 2) if amount > 0 else None

        except (ValueError, TypeError):
            return None

    @classmethod
    def extract_amounts(cls, text: str) -> Dict[str, Optional[float]]:
        """Extrait les montants d'une facture avec validation stricte."""
        text = re.sub(r'\s+', ' ', text).strip()

        # Initialiser les résultats
        amounts = {
            'ttc': None,
            'ht': None,
            'total': None,
            'tax': None,
            'tax_rate': None
        }

        # Extraire tous les montants avec leur contexte
        for amount_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    value_str = match.group(1).strip()
                    if amount_type == 'tax_rate':
                        try:
                            value = float(value_str)
                            if 0 < value <= 100:
                                amounts[amount_type] = value
                        except ValueError:
                            continue
                    else:
                        value = cls.clean_amount(value_str)
                        if value is not None and (amounts[amount_type] is None or value > amounts[amount_type]):
                            amounts[amount_type] = value

        # Déterminer le total et le sous-total
        result = {'total': None, 'subtotal': None}

        # Si on a un montant TTC explicite, c'est le total
        if amounts['ttc'] is not None:
            result['total'] = amounts['ttc']
            # Si on a aussi le montant HT, c'est le sous-total
            if amounts['ht'] is not None:
                result['subtotal'] = amounts['ht']

        # Si on a un montant HT explicite sans TTC
        elif amounts['ht'] is not None:
            result['subtotal'] = amounts['ht']
            # Si on a la TVA, on peut calculer le total
            if amounts['tax'] is not None:
                result['total'] = round(amounts['ht'] + amounts['tax'], 2)
            elif amounts['tax_rate'] is not None:
                result['total'] = round(amounts['ht'] * (1 + amounts['tax_rate'] / 100), 2)

        # Si on a juste un total sans précision
        elif amounts['total'] is not None:
            result['total'] = amounts['total']

        # Validation finale
        if result['total'] is not None and result['subtotal'] is not None:
            if result['total'] < result['subtotal']:
                logger.warning("Le total est inférieur au sous-total, possible erreur")
                result['total'], result['subtotal'] = result['subtotal'], result['total']

        return result


def test_amount_extractor():
    """Tests de l'extracteur de montants."""
    test_cases = [
        "Total TTC : 1234,56 €",
        "Montant HT : 1000,00\nTVA 20% : 200,00\nTotal : 1200,00",
        "Prix total : EUR 1.234,56",
        "Sous-total : 1000,00 €\nTotal : 1200,00 €",
        "€ 1234,56 TTC",
        "1.234,56 € HT",
        "Total : 1,234.56 €",
        "Montant HT : 1.234,56 €",
        "Prix : 1234.56 €",
        "Facture : 1234.56 €",
        "Montant : 1,234.56",
        "1234.56",
        "HT : 1000.00 € TTC : 1200.00 €",
        "Base HT : 1000.00 €\nTVA (20%) : 200.00 €\nTotal TTC : 1200.00 €",
    ]

    extractor = FinalAmountExtractor()
    for test in test_cases:
        results = extractor.extract_amounts(test)
        print(f"\nTest: {test}")
        print(f"Résultats: {results}")


if __name__ == "__main__":
    test_amount_extractor()
