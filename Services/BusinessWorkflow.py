from Models.Alert import Alert
from Services.PaymentService import PaymentService
from Services.alert_service import AlertService
from Services.invoice_service import InvoiceService


class BusinessWorkflow:
    def __init__(self, db_session):
        self.db_session = db_session  # Ajouter cette ligne
        self.invoice_service = InvoiceService(db_session)
        self.payment_service = PaymentService(db_session)
        self.alert_service = AlertService(db_session)

    def execute_sales_process(self, client_id, items, due_date, payment_method):
        try:
            # Étape 1: Création de la facture
            invoice = self.invoice_service.create_invoice(client_id, items, due_date)

            # Étape 2: Paiement
            transaction = self.payment_service.process_payment(
                invoice.id,
                payment_method,
                invoice.total
            )

            # Étape 3: Vérification des alertes
            self.alert_service.check_pending_payments()
            self.alert_service.check_expired_products()

            return {
                'status': 'success',
                'invoice': invoice,
                'transaction': transaction
            }

        except Exception as e:
            # Gestion des erreurs et création d'alerte
            alert = Alert(
                type='system',
                message=str(e),
                related_type='transaction',
                status='critical'
            )
            self.db_session.add(alert)  # Correction ici
            self.db_session.commit()

            return {
                'status': 'error',
                'message': str(e)
            }
