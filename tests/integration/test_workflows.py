from datetime import datetime, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Models.Client import Base, Client
from Models.Product import Product
from Services.BusinessWorkflow import BusinessWorkflow
from tests.unit.factories import ClientFactory, ProductFactory, CategoryFactory, SupplierFactory

# Setup for your database session fixture
@pytest.fixture
def db_session():
    engine = create_engine('sqlite:///invoices.db')  # Use your actual DB URI
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


def test_complete_sales_workflow(db_session):
    # Setup
    client = ClientFactory()
    category = CategoryFactory(name="Electronics")
    supplier = SupplierFactory()
    product = ProductFactory(
        name="Laptop Premium",
        stock_quantity=50,
        unit_price=1500.00,
        category=category,
        supplier=supplier
    )

    db_session.add_all([client, category, supplier, product])
    db_session.commit()

    # Assertions on setup
    assert client.id is not None
    assert category.id is not None
    assert supplier.id is not None
    assert product.id is not None
    assert product.category is not None
    assert product.supplier is not None

    # Execute workflow
    workflow = BusinessWorkflow(db_session)
    result = workflow.execute_sales_process(
        client_id=client.id,
        items=[{'product_id': product.id, 'quantity': 10}],
        due_date=datetime.now() + timedelta(days=30),
        payment_method='check'
    )

    # Assertions on workflow execution
    assert result['status'] == 'success'
    invoice = result['invoice']
    transaction = result['transaction']

    assert invoice.status == 'paid'
    assert transaction.amount == invoice.total
    assert len(transaction.checks) == 1
    assert transaction.checks[0].status == 'pending'

    # Refresh product stock after transaction
    db_session.refresh(product)
    assert product.stock_quantity == 40
