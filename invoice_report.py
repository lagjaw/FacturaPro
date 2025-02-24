from datetime import datetime

# Stocker les factures de la journée dans une variable globale
daily_invoices = []

# Fonction pour ajouter une facture au rapport
def add_invoice_to_report(processed_invoice):
    # Assurez-vous que processed_invoice a la structure correcte
    if 'total' in processed_invoice:
        try:
            # Convertir total en float si nécessaire
            processed_invoice['total'] = float(processed_invoice['total'])
            daily_invoices.append(processed_invoice)
        except ValueError:
            print(f"Erreur: Total de la facture invalide - {processed_invoice['total']}")
    else:
        print("Erreur: Facture sans montant total.")

# Fonction pour générer le rapport de la journée comptable
def generate_daily_report():
    if not daily_invoices:
        print("Aucune facture traitée pour aujourd'hui.")
        return None  # Si aucune facture n'a été ajoutée

    total_ht = sum(float(inv['total']) for inv in daily_invoices)
    total_tva = total_ht * 0.20  # Assuming 20% VAT
    total_global = total_ht + total_tva

    report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "number_of_invoices": len(daily_invoices),
        "total_ht": total_ht,
        "total_tva": total_tva,
        "total_global": total_global,
        "invoices": daily_invoices
    }

    # Optionnel: Vider la liste des factures après génération du rapport
    daily_invoices.clear()

    return report
