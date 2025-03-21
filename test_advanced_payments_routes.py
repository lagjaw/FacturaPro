import pytest
from fastapi.testclient import TestClient
from main import app  # Assuming your FastAPI app is defined in main.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import get_db_session
from Models import Base, Check

# Setup for testing
@pytest.fixture(scope='module')
def test_db():
    # Create a new database for testing
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    connection = engine.connect()
    transaction = connection.begin()
    yield connection
    transaction.rollback()
    connection.close()

@pytest.fixture
def db_session(test_db):
    """Create a new session for each test."""
    session = sessionmaker(bind=test_db)()
    yield session
    session.close()

@pytest.fixture
def client(db_session):
    """Create a TestClient for the FastAPI app."""
    app.dependency_overrides[get_db_session] = lambda: db_session
    with TestClient(app) as c:
        yield c

def test_divide_check(client):
    """Test dividing a check via the API."""
    # Setup: Create a check in the database
    check = Check(id='1', check_number='123456', amount=1000.00, status='pending', check_date='2023-01-01', bank_name='Test Bank')
    db_session = next(get_db_session())
    db_session.add(check)
    db_session.commit()

    response = client.post("/divide/1", json={"amounts": [500.00, 500.00]})
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_replace_check(client):
    """Test replacing a check via the API."""
    # Setup: Create a check in the database
    old_check = Check(id='1', check_number='123456', amount=1000.00, status='pending', check_date='2023-01-01', bank_name='Test Bank')
    db_session = next(get_db_session())
    db_session.add(old_check)
    db_session.commit()

    new_check_info = {
        "check_number": "654321",
        "amount": 2000.00,
        "bank_name": "New Bank",
        "bank_branch": "New Branch",
        "bank_account": "9876543210",
        "swift_code": "NEWBANK"
    }

    response = client.post("/replace/1", json=new_check_info)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

# Additional tests for other endpoints can be added similarly
