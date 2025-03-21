import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import get_db_session
from Services.advanced_payment_service import AdvancedPaymentService
from Models import Base, Check, PaymentTransaction

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
def payment_service(db_session):
    """Fixture for the AdvancedPaymentService."""
    return AdvancedPaymentService(db_session)

def test_divide_check(payment_service):
    """Test dividing a check."""
    # Setup: Create a check in the database
    check = Check(id='1', check_number='123456', amount=1000.00, status='pending', check_date='2023-01-01', bank_name='Test Bank')
    payment_service.db.add(check)
    payment_service.db.commit()

    # Test dividing the check
    amounts = [500.00, 500.00]
    result = payment_service.divide_check(check.id, amounts)

    assert result['check_number'] == check.check_number
    assert len(result['divisions']) == 2

def test_replace_check(payment_service):
    """Test replacing a check."""
    # Setup: Create a check in the database
    old_check = Check(id='1', check_number='123456', amount=1000.00, status='pending', check_date='2023-01-01', bank_name='Test Bank')
    payment_service.db.add(old_check)
    payment_service.db.commit()

    new_check_info = { 
        'check_number': '654321',
        'amount': 2000.00,
        'bank_name': 'New Bank',
        'bank_branch': 'New Branch',
        'bank_account': '9876543210',
        'swift_code': 'NEWBANK'
    }

    result = payment_service.replace_check(old_check.id, new_check_info)

    assert result['old_check']['number'] == old_check.check_number
    assert result['new_check']['number'] == new_check_info['check_number']

# Additional tests for other methods can be added similarly
