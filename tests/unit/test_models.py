# tests/unit/test_models.py
import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import uuid

from Models.Alert import Alert
from Models.Category import Category
from Models.Check import Check
from Models.CheckDivision import CheckDivision
from Models.Client import Client
from Models.Invoice import Invoice
from Models.InvoiceProduct import InvoiceProduct
from Models.Product import Product
from Models.Supplier import Supplier
from Models.PaymentTransaction import PaymentTransaction


def test_alert_model(db_session: Session):
    # Test création d'alerte
    alert = Alert(
        type="security",
        message="Test alert",
        related_id=str(uuid.uuid4()),
        related_type="system"
    )

    db_session.add(alert)
    db_session.commit()

    assert alert.id is not None
    assert alert.status == "pending"
    assert isinstance(alert.created_at, datetime)
    assert alert.updated_at >= alert.created_at


def test_category_relationships(db_session: Session):
    # Test relation Category ↔ Product
    category = Category(name="Electronics")
    product = Product(name="Smartphone", category=category)

    db_session.add_all([category, product])
    db_session.commit()

    assert category.products == [product]
    assert product.category == category


def test_check_division_workflow(db_session: Session):
    # Test workflow Check ↔ CheckDivision
    check = Check(
        check_number="CHK-001",
        amount=15000,
        bank_name="Test Bank",
        check_date=datetime.now()
    )

    divisions = [
        CheckDivision(amount=5000),
        CheckDivision(amount=10000)
    ]
    check.check_divisions = divisions

    db_session.add(check)
    db_session.commit()

    assert len(check.check_divisions) == 2
    assert sum(d.amount for d in check.check_divisions) == check.amount


def test_client_transaction_relationship(db_session: Session):
    # Test relations Client ↔ Transaction
    client = Client(name="Test Client")
    transaction = PaymentTransaction(
        amount=1000,
        payment_method="cash",
        client=client
    )

    db_session.add(client)
    db_session.commit()

    assert client.paymenttransactions == [transaction]
    assert transaction.client == client


def test_invoice_validation(db_session: Session):
    # Test contraintes métier sur Invoice
    invoice = Invoice(
        invoice_number="INV-001",
        due_date=datetime.now() + timedelta(days=30),
        bill_to="Test Client",
        total=1000
    )

    with pytest.raises(IntegrityError):
        # Test missing required field
        invoice.date = None
        db_session.add(invoice)
        db_session.commit()


def test_product_stock_management(db_session: Session):
    # Test gestion de stock
    product = Product(
        name="Laptop",
        stock_quantity=50,
        unit_price=999.99
    )

    db_session.add(product)
    db_session.commit()

    # Test stock update
    product.stock_quantity -= 10
    db_session.commit()

    updated_product = db_session.query(Product).get(product.id)
    assert updated_product.stock_quantity == 40


def test_supplier_products_relationship(db_session: Session):
    # Test relation Supplier ↔ Product
    supplier = Supplier(name="Tech Supplier")
    product = Product(name="Processor", supplier=supplier)

    db_session.add(supplier)
    db_session.commit()

    assert supplier.products == [product]
    assert product.supplier == supplier


def test_transaction_status_flow(db_session: Session):
    # Test workflow de statut
    transaction = PaymentTransaction(
        amount=500,
        payment_method="credit_card",
        status="pending"
    )

    db_session.add(transaction)
    db_session.commit()

    # Test status transition
    transaction.status = "completed"
    db_session.commit()

    updated_transaction = db_session.query(PaymentTransaction).get(transaction.id)
    assert updated_transaction.status == "completed"


def test_invoice_product_association(db_session: Session):
    # Test association Invoice ↔ Product via InvoiceProduct
    invoice = Invoice(invoice_number="INV-002")
    product = Product(name="Keyboard")
    association = InvoiceProduct(
        invoice=invoice,
        product=product,
        quantity=2,
        unit_price=49.99
    )

    db_session.add_all([invoice, product, association])
    db_session.commit()

    assert invoice.invoice_products == [association]
    assert product.invoice_products == [association]
    assert association.total_price == 2 * 49.99


def test_expiration_alerts(db_session: Session):
    # Test alerte d'expiration
    product = Product(
        name="Yogurt",
        expiration_date=datetime.now() - timedelta(days=1)
    )

    db_session.add(product)
    db_session.commit()

    # Vérifier qu'une alerte est générée
    alert = db_session.query(Alert).filter_by(related_id=product.id).first()
    assert alert is not None
    assert "expiration" in alert.type