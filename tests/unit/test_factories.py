import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from Models.Category import Category
from Models.Supplier import Supplier
from Models.Product import Product
from tests.unit.factories import ProductFactory, CategoryFactory, SupplierFactory

@pytest.fixture
def db_session():
    """ Crée une base de données en mémoire pour les tests """
    engine = create_engine('sqlite:///:memory:')  # ✅ Base en mémoire
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(engine)

def test_product_creation(db_session):
    # Création des objets via les factories
    category = CategoryFactory(
        id=str(uuid.uuid4()),
        name="Electronics",
        created_at=datetime.now()
    )

    supplier = SupplierFactory(
        id=str(uuid.uuid4()),
        name="Tech Supplier",
        address="123 Supplier Street",
        created_at=datetime.now()
    )

    product = ProductFactory(
        id=str(uuid.uuid4()),
        name="Laptop Premium",
        stock_quantity=50,
        unit_price=1500.00,
        category_id=category.id,  # ✅ Stocke directement l’ID
        supplier_id=supplier.id,  # ✅ Stocke directement l’ID
        created_at=datetime.now()
    )

    db_session.add_all([category, supplier, product])
    db_session.commit()

    # Récupération et vérifications
    retrieved_product = db_session.query(Product).filter_by(id=product.id).first()
    assert retrieved_product is not None
    assert retrieved_product.name == "Laptop Premium"
    assert retrieved_product.category_id == category.id  # ✅ Vérification via l’ID
    assert retrieved_product.supplier_id == supplier.id  # ✅ Vérification via l’ID
