from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from contextlib import asynccontextmanager, contextmanager
import sqlite3
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
)
logger = logging.getLogger(__name__)

# Database configuration
DB_PATH = Path('invoices.db')
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# SQLAlchemy setup
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession)
Base = declarative_base()

@asynccontextmanager
async def get_db_session():
    """Context manager for SQLAlchemy sessions"""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logging.error(f"Database session error: {e}")
            raise

@contextmanager
def get_db_connection():
    """Context manager for SQLite connections"""
    conn = None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()

async def init_db():
    """Initialize database tables"""
    try:
        # Ensure the database directory exists
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Import all models to ensure they are registered with SQLAlchemy
        from Models.Check import Check
        from Models.CheckDivision import CheckDivision
        from Models.PaymentTransaction import PaymentTransaction
        from Models.Invoice import Invoice
        from Models.Client import Client
        from Models.Category import Category
        from Models.Product import Product
        from Models.Supplier import Supplier
        from Models.InvoiceProduct import InvoiceProduct
        from Models.Alert import Alert

        # Create all tables
        async with engine.begin() as conn:
            # Drop the invoices table if it exists
            await conn.run_sync(Base.metadata.create_all)

        logger.info("SQLAlchemy tables created successfully")

        # Create additional tables using raw SQL for additional indexes and constraints
        async with get_db_session() as session:
            # Create categories table
            await session.execute(text('''
                CREATE TABLE IF NOT EXISTS categories (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))

            # Create suppliers table
            await session.execute(text('''
                CREATE TABLE IF NOT EXISTS suppliers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    contact_info TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))

            # Create products table
            await session.execute(text('''
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    stock_quantity INTEGER DEFAULT 0,
                    unit_price NUMERIC NOT NULL DEFAULT 0,
                    expiration_date TIMESTAMP,
                    stock_alert_threshold INTEGER DEFAULT 10,
                    expiration_alert_threshold INTEGER DEFAULT 30,
                    description TEXT,
                    category_id TEXT,
                    supplier_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories (id),
                    FOREIGN KEY (supplier_id) REFERENCES suppliers (id)
                )
            '''))

            # Create clients table
            await session.execute(text('''
                CREATE TABLE IF NOT EXISTS clients (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    revenue NUMERIC DEFAULT 0,
                    email TEXT,
                    address TEXT,
                    phone TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))

            # Create invoices table
            await session.execute(text('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id TEXT PRIMARY KEY,
                    client_id Text NOT NULL,
                    invoice_number TEXT UNIQUE NOT NULL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    due_date TIMESTAMP NOT NULL,
                    bill_to TEXT NOT NULL,
                    total NUMERIC DEFAULT 0,
                    subtotal NUMERIC DEFAULT 0,
                    tax NUMERIC DEFAULT 0,
                    gstin TEXT,
                    discount NUMERIC DEFAULT 0,
                    bank_name TEXT,
                    branch_name TEXT,
                    bank_account_number TEXT,
                    bank_swift_code TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    items TEXT,
                    FOREIGN KEY (client_id) REFERENCES clients (id)                                 
                )
            '''))

            # Create invoice_products table
            await session.execute(text('''
                CREATE TABLE IF NOT EXISTS invoice_products (
                    invoice_id TEXT,
                    product_id TEXT,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    unit_price NUMERIC NOT NULL DEFAULT 0,
                    total_price NUMERIC NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (invoice_id, product_id),
                    FOREIGN KEY (invoice_id) REFERENCES invoices (id),
                    FOREIGN KEY (product_id) REFERENCES products (id)
                )
            '''))

            # Create payment_transactions table
            await session.execute(text('''
                CREATE TABLE IF NOT EXISTS payment_transactions (
                    id TEXT PRIMARY KEY,
                    client_id TEXT,
                    invoice_id TEXT,
                    amount NUMERIC NOT NULL DEFAULT 0,
                    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    payment_method TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    due_date TIMESTAMP,
                    paid_amount NUMERIC DEFAULT 0,
                    remaining_amount NUMERIC DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients (id),
                    FOREIGN KEY (invoice_id) REFERENCES invoices (id)
                )
            '''))

            # Create checks table
            await session.execute(text('''
                CREATE TABLE IF NOT EXISTS checks (
                    id TEXT PRIMARY KEY,
                    transaction_id TEXT NOT NULL,
                    check_number TEXT NOT NULL,
                    amount NUMERIC NOT NULL,
                    status TEXT DEFAULT 'pending',
                    check_date TEXT NOT NULL,
                    bank_name TEXT NOT NULL,
                    bank_branch TEXT,
                    bank_account TEXT,
                    swift_code TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (transaction_id) REFERENCES payment_transactions (id)
                )
            '''))

            # Create check_divisions table
            await session.execute(text('''
                CREATE TABLE IF NOT EXISTS check_divisions (
                    id TEXT PRIMARY KEY,
                    check_id TEXT NOT NULL,
                    amount NUMERIC NOT NULL,
                    division_date TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (check_id) REFERENCES checks (id)
                )
            '''))

            # Create alerts table
            await session.execute(text('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    related_id TEXT,
                    related_type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))

            await session.commit()
            logger.info("Database tables initialized successfully")

    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

async def check_connection():
    """Test database connection and initialize if needed"""
    try:
        async with get_db_session() as session:
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = result.fetchall()
            if not tables:
                await init_db()
            return True
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return False

# Initialize database on module import
if __name__ == "__main__":
    import asyncio
    if not asyncio.run(check_connection()):
        logger.error("Failed to initialize database")
        raise RuntimeError("Database initialization failed")

# Re-export connection functions for backward compatibility
get_db = get_db_session  # For raw SQL