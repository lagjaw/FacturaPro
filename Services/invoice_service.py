from datetime import datetime
from Models.Alert import Alert
from Models.Client import Client
from Models.Invoice import Invoice
from Models.InvoiceProduct import InvoiceProduct
from Models.Product import Product


class InvoiceService:
    def __init__(self, db_session):
        self.db = db_session

    def create_invoice(self, client_id, items, due_date):
        # Validation du client
        client = self.db.query(Client).get(client_id)
        if not client:
            raise ValueError("Client introuvable")

        # Création de la facture
        invoice = Invoice(
            invoice_number=self._generate_invoice_number(),
            due_date=due_date,
            bill_to=client.name,
            client_id=client_id,
            status='draft'
        )

        # Ajout des articles
        total = 0
        for item in items:
            product = self.db.query(Product).get(item['product_id'])
            if not product:
                raise ValueError(f"Produit {item['product_id']} introuvable")

            if product.stock_quantity < item['quantity']:
                raise ValueError(f"Stock insuffisant pour {product.name}")

            # Création de la liaison InvoiceProduct
            invoice_product = InvoiceProduct(
                product_id=product.id,
                quantity=item['quantity'],
                unit_price=product.unit_price,
                total_price=product.unit_price * item['quantity']
            )
            invoice.invoice_products.append(invoice_product)

            # Mise à jour du stock
            product.stock_quantity -= item['quantity']
            total += invoice_product.total_price

        # Calcul des totaux
        invoice.subtotal = total
        invoice.tax = total * 0.2  # Supposons une TVA de 20%
        invoice.total = invoice.subtotal + invoice.tax

        self.db.add(invoice)
        self.db.commit()

        # Vérification des alertes de stock
        self._check_stock_alerts()

        return invoice

    def _generate_invoice_number(self):
        # Logique de génération de numéro de facture
        return f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    def _check_stock_alerts(self):
        products = self.db.query(Product).filter(
            Product.stock_quantity <= Product.stock_alert_threshold
        ).all()

        for product in products:
            alert = Alert(
                type='stock',
                message=f"Stock faible pour {product.name}",
                related_id=product.id,
                related_type='product',
                status='active'
            )
            self.db.add(alert)
        self.db.commit()