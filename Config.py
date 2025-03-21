from pydantic_settings import BaseSettings
from typing import Optional, List, Literal
from functools import lru_cache

def get_default_cors_origins() -> List[str]:
    return ["*"]

def get_default_cors_methods() -> List[str]:
    return ["*"]

def get_default_cors_headers() -> List[str]:
    return ["*"]

def get_default_allowed_extensions() -> List[str]:
    return [".pdf", ".jpg", ".jpeg", ".png"]

def get_default_payment_reminder_days() -> List[int]:
    return [7, 3, 1]

def get_default_report_formats() -> List[str]:
    return ["csv", "pdf", "xlsx"]

def get_test_payment_reminder_days() -> List[int]:
    return [1]

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "FACTU Pro API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API for FACTU Pro Commercial Management Application"

    # Server Configuration
    HOST: str = "0.0.0.0"  # Change to localhost for local development
    PORT: int = 8000
    WORKERS: int = 1
    RELOAD: bool = False

    # Database Configuration
    DATABASE_URL: str = "C:/Users/User/Desktop/PycharmProjects/pythonProject5/invoices.db"

    # CORS Configuration
    CORS_ORIGINS: List[str] = None
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = None
    CORS_HEADERS: List[str] = None

    # Security Configuration
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Email Configuration
    SMTP_HOST: Optional[str] = "smtp.gmail.com"
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = "aybetude@gmail.com"
    SMTP_PASSWORD: Optional[str] = "your-app-specific-password"

    # SMS Configuration
    SMS_PROVIDER: Optional[str] = "twilio"
    SMS_API_KEY: Optional[str] = "your-twilio-api-key"
    SMS_API_SECRET: Optional[str] = "your-twilio-api-secret"

    # File Upload Configuration
    UPLOAD_DIR: str = "C:/Users/User/Desktop/PycharmProjects/pythonProject5/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = None

    # Logging Configuration
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Invoice Processing Configuration
    INVOICE_TEMPLATE_DIR: str = "C:/Users/User/Desktop/PycharmProjects/pythonProject5/templates"
    OCR_ENABLED: bool = True
    OCR_LANGUAGE: str = "fra"  # French language for OCR

    # Payment Configuration
    CHECK_DIVISION_LIMIT: float = 10000.0  # Limit for automatic check division
    DEFAULT_PAYMENT_DUE_DAYS: int = 30
    PAYMENT_REMINDER_DAYS: List[int] = None  # Will be set in __init__

    # Client Configuration
    KEY_ACCOUNT_REVENUE_THRESHOLD: float = 100000.0  # Revenue threshold for key account status
    INACTIVE_DAYS_THRESHOLD: int = 180  # Days of inactivity before client marked as inactive

    # Stock Configuration
    LOW_STOCK_THRESHOLD: int = 10
    EXPIRATION_WARNING_DAYS: int = 30  # Days before expiration to start warnings
    STOCK_CHECK_INTERVAL_HOURS: int = 24

    # Report Configuration
    REPORT_EXPORT_FORMATS: List[str] = None  # Will be set in __init__
    DEFAULT_REPORT_PERIOD_DAYS: int = 30
    REPORT_TIMEZONE: str = "Europe/Paris"

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "validate_default": True
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.CORS_ORIGINS = self.CORS_ORIGINS or get_default_cors_origins()
        self.CORS_METHODS = self.CORS_METHODS or get_default_cors_methods()
        self.CORS_HEADERS = self.CORS_HEADERS or get_default_cors_headers()
        self.ALLOWED_EXTENSIONS = self.ALLOWED_EXTENSIONS or get_default_allowed_extensions()
        self.PAYMENT_REMINDER_DAYS = self.PAYMENT_REMINDER_DAYS or get_default_payment_reminder_days()
        self.REPORT_EXPORT_FORMATS = self.REPORT_EXPORT_FORMATS or get_default_report_formats()

@lru_cache()
def get_environment_settings() -> Settings:
    return Settings()
