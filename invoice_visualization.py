# Fonction pour visualiser les informations de la facture
def visualize_invoice_data(processed_invoice):
    print("Informations de la facture:")
    for key, value in processed_invoice.items():
        print(f"{key}: {value}")
