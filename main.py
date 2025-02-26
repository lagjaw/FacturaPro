from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
from datetime import datetime

from Config import get_environment_settings
from Routes.advanced_payments_routes import advanced_payments_router

# Import all routes

from Routes.alert_routes import router as alert_router
from Routes.check_division_routes import router as check_division_router
from Routes.check_routes import router as check_router
from Routes.clientRoutes import router as client_router
from Routes.email_routes import router as email_router
from Routes.invoice_routes import router as invoice_router
from Routes.invoice_processing_routes import router as invoice_processing_router
from Routes.notification_routes import router as notification_router
from Routes.payment_routes import router as payment_router
from Routes.product_routes import router as product_router
from Routes.report_routes import router as report_router
from Routes.sms_routes import router as sms_router
from Routes.stock_routes import router as stock_router
from Routes.transaction_alert_routes import router as transaction_alert_router
from Routes.transaction_routes import router as transaction_router
from Routes.unpaid_routes import router as unpaid_router
from Routes.communications_routes import router as communications_router
from database import init_db

# Get settings for current environment
settings = get_environment_settings()

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Database initialization on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        init_db()
        logger.info("Database initialized successfully on startup")
    except Exception as e:
        logger.error(f"Failed to initialize database on startup: {e}")
        raise

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Add Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Define all routers with their prefixes
ROUTERS = [
    (advanced_payments_router, "/payments/advanced"),
    (alert_router, "/alerts"),
    (check_division_router, "/checks/division"),
    (check_router, "/checks"),
    (client_router, "/clients"),
    (email_router, "/email"),
    (invoice_router, "/invoices"),
    (invoice_processing_router, "/invoice-processing"),
    (notification_router, "/notifications"),
    (payment_router, "/payments"),
    (product_router, "/products"),
    (report_router, "/reports"),
    (sms_router, "/sms"),
    (stock_router, "/stock"),
    (transaction_alert_router, "/transactions/alerts"),
    (transaction_router, "/transactions"),
    (unpaid_router, "/unpaid"),
    (communications_router, "/communications")  # Added communications router
]

# Include all routers with their specific prefixes
for router, prefix in ROUTERS:
    app.include_router(
        router,
        prefix=f"{settings.API_V1_STR}{prefix}",
        tags=[prefix.strip("/").title()]
    )


@app.get("/")
async def root():
    """Root endpoint providing API information"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "documentation": "/docs",
        "redoc": "/redoc",
        "environment": settings.model_config["env_file"]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION,
        "environment": settings.model_config["env_file"],
        "database": settings.DATABASE_URL
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception handler: {exc}", exc_info=True)
    return {
        "status": "error",
        "message": str(exc),
        "type": type(exc).__name__
    }


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting {settings.PROJECT_NAME} on http://{settings.HOST}:{settings.PORT}")
    logger.info(f"Environment: {settings.model_config['env_file']}")
    logger.info(f"Database: {settings.DATABASE_URL}")

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )
