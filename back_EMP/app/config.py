"""
Configuration - Lecture des variables d'environnement depuis .env
"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Database
    DB_SERVER: str = os.getenv("DB_SERVER", "localhost\\SQLEXPRESS")
    DB_NAME: str = os.getenv("DB_NAME", "OCR_Extraction_DB")
    DB_DRIVER: str = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    DB_TRUSTED_CONNECTION: str = os.getenv("DB_TRUSTED_CONNECTION", "yes")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_ENCRYPT: str = os.getenv("DB_ENCRYPT", "no")
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    ACCESS_COOKIE_NAME: str = os.getenv("ACCESS_COOKIE_NAME", "emp_access_token")
    REFRESH_COOKIE_NAME: str = os.getenv("REFRESH_COOKIE_NAME", "emp_refresh_token")
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "true").lower() in ("true", "1", "yes")
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax")
    COOKIE_DOMAIN: str = os.getenv("COOKIE_DOMAIN", "")
    COOKIE_PATH: str = os.getenv("COOKIE_PATH", "/")

    # SMTP / Mailtrap
    SMTP_HOST: str = os.getenv("SMTP_HOST", "sandbox.smtp.mailtrap.io")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "EMP.OCR@example.com")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    
    # OCR
    TESSERACT_PATH: str = os.getenv("TESSERACT_PATH", "")
    POPPLER_PATH: str = os.getenv("POPPLER_PATH", "")
    OCR_DEBUG_ZONES: bool = os.getenv("OCR_DEBUG_ZONES", "false").lower() in ("true", "1", "yes")
    OCR_ENGINE_PRIMARY: str = os.getenv("OCR_ENGINE_PRIMARY", "paddle")
    OCR_ENABLE_PADDLE_FALLBACK: bool = os.getenv("OCR_ENABLE_PADDLE_FALLBACK", "true").lower() in ("true", "1", "yes")
    OCR_ENABLE_TESSERACT_FALLBACK: bool = os.getenv("OCR_ENABLE_TESSERACT_FALLBACK", "true").lower() in ("true", "1", "yes")
    OCR_ENABLE_PPSTRUCTURE: bool = os.getenv("OCR_ENABLE_PPSTRUCTURE", "false").lower() in ("true", "1", "yes")
    OCR_CONFIDENCE_THRESHOLD: float = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.62"))
    OCR_PADDLE_LANG: str = os.getenv("OCR_PADDLE_LANG", "en")
    # Second Paddle model (e.g. "fr") for identity zones when the primary lang fails business validation.
    OCR_PADDLE_LANG_FALLBACK: str = os.getenv("OCR_PADDLE_LANG_FALLBACK", "fr").strip()
    # Partie 1 — contrôle qualité upload
    OCR_MIN_PAGE_WIDTH: int = int(os.getenv("OCR_MIN_PAGE_WIDTH", "1200"))
    OCR_MIN_PAGE_HEIGHT: int = int(os.getenv("OCR_MIN_PAGE_HEIGHT", "1600"))
    OCR_MIN_ESTIMATED_DPI: float = float(os.getenv("OCR_MIN_ESTIMATED_DPI", "200"))
    OCR_MIN_BLUR_SCORE: float = float(os.getenv("OCR_MIN_BLUR_SCORE", "35"))
    OCR_QUALITY_STRICT: bool = os.getenv("OCR_QUALITY_STRICT", "false").lower() in ("true", "1", "yes")
    OCR_QUALITY_BLOCK_ON_FAIL: bool = os.getenv("OCR_QUALITY_BLOCK_ON_FAIL", "false").lower() in ("true", "1", "yes")
    # Partie 6 — pré-traitement, cellules bandeau, debug crops
    OCR_PREPROCESS_ENHANCE: bool = os.getenv("OCR_PREPROCESS_ENHANCE", "true").lower() in ("true", "1", "yes")
    OCR_ENABLE_HEADER_CELL_OCR: bool = os.getenv("OCR_ENABLE_HEADER_CELL_OCR", "true").lower() in ("true", "1", "yes")
    OCR_DEBUG_SAVE_DIR: str = os.getenv("OCR_DEBUG_SAVE_DIR", "").strip()
    # Phase 3 — sauvetages par marque connue (démo / tests ; désactivé en prod par défaut)
    OCR_ENABLE_BRAND_RESCUES: bool = os.getenv("OCR_ENABLE_BRAND_RESCUES", "false").lower() in (
        "true",
        "1",
        "yes",
    )

    # Nextcloud GED (WebDAV)
    NEXTCLOUD_ENABLED: bool = os.getenv("NEXTCLOUD_ENABLED", "false").lower() in ("true", "1", "yes")
    NEXTCLOUD_BASE_URL: str = os.getenv("NEXTCLOUD_BASE_URL", "")
    NEXTCLOUD_USERNAME: str = os.getenv("NEXTCLOUD_USERNAME", "")
    NEXTCLOUD_PASSWORD: str = os.getenv("NEXTCLOUD_PASSWORD", "")
    NEXTCLOUD_UPLOAD_ROOT: str = os.getenv("NEXTCLOUD_UPLOAD_ROOT", "EMP-SmartOCR")
    NEXTCLOUD_TIMEOUT_SECONDS: int = int(os.getenv("NEXTCLOUD_TIMEOUT_SECONDS", "20"))
    NEXTCLOUD_VERIFY_SSL: bool = os.getenv("NEXTCLOUD_VERIFY_SSL", "true").lower() in ("true", "1", "yes")
    NEXTCLOUD_REQUIRED: bool = os.getenv("NEXTCLOUD_REQUIRED", "false").lower() in ("true", "1", "yes")
    
    # API factures (historique unifié — optionnel)
    INVOICE_API_URL: str = os.getenv("INVOICE_API_URL", "http://localhost:8001").strip()
    INVOICE_API_TIMEOUT_SECONDS: int = int(os.getenv("INVOICE_API_TIMEOUT_SECONDS", "120"))
    INVOICE_INTERNAL_API_KEY: str = os.getenv("INVOICE_INTERNAL_API_KEY", "").strip()

    # Serveur ERP S2 (migration — URL exemple, remplacer par l'ERP réel)
    ERP_SERVICE_URL: str = os.getenv("ERP_SERVICE_URL", "http://localhost:8002").strip()

    # Fichiers DUM locaux (si GED Nextcloud indisponible)
    DUM_LOCAL_STORAGE_DIR: str = os.getenv("DUM_LOCAL_STORAGE_DIR", "storage/dum")

    # CORS
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "")
    
    # APP DEBUG & ENV
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    ENV: str = os.getenv("ENV", "development")
    
    class Config:
        env_file = ".env"


settings = Settings()

if not settings.SECRET_KEY or len(settings.SECRET_KEY.strip()) < 32:
    raise RuntimeError(
        "Configuration error: SECRET_KEY is required and must be at least 32 characters long."
    )
