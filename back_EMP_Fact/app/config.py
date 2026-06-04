import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # SQL Server (même base que back_EMP — OCR_Extraction_DB)
    DB_SERVER: str = "localhost\\SQLEXPRESS"
    DB_NAME: str = "OCR_Extraction_DB"
    DB_DRIVER: str = "ODBC Driver 18 for SQL Server"
    DB_TRUSTED_CONNECTION: str = "yes"
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_ENCRYPT: str = "no"
    # Override complet optionnel (ex. tests sqlite)
    DATABASE_URL: str = ""

    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_COOKIE_NAME: str = "emp_access_token"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Clé partagée avec back_EMP (proxy serveur → serveur uniquement)
    INVOICE_INTERNAL_API_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ALLOWED_ORIGINS: str = ""
    DEBUG: bool = False

    TESSERACT_PATH: str = ""
    OCR_ENGINE_PRIMARY: str = "paddle"
    OCR_ENABLE_PADDLE: bool = True
    OCR_PADDLE_LANG: str = "en"
    OCR_TESSERACT_LANG: str = "eng"
    OCR_PREPROCESS_ENHANCE: bool = True
    OCR_PDF_MAX_PAGES: int = 2
    OCR_PDF_ZOOM: float = 2.5

    # Nextcloud GED (aligné DUM)
    NEXTCLOUD_ENABLED: bool = False
    NEXTCLOUD_BASE_URL: str = ""
    NEXTCLOUD_USERNAME: str = ""
    NEXTCLOUD_PASSWORD: str = ""
    NEXTCLOUD_UPLOAD_ROOT: str = "EMP-SmartOCR"
    NEXTCLOUD_INVOICE_SUBFOLDER: str = "factures"
    NEXTCLOUD_TIMEOUT_SECONDS: int = 20
    NEXTCLOUD_CONNECT_TIMEOUT_SECONDS: int = 3
    NEXTCLOUD_VERIFY_SSL: bool = True
    NEXTCLOUD_REQUIRED: bool = False

    # Fichiers facture locaux (si GED Nextcloud indisponible)
    INVOICE_LOCAL_STORAGE_DIR: str = "storage/invoices"

    # Facture : Tesseract avant Paddle (plus rapide sur image/PDF scanné léger)
    OCR_INVOICE_TESSERACT_FIRST: bool = True


settings = Settings()


def internal_api_key() -> str:
    """Clé proxy back_EMP → back_EMP_Fact (défaut : SECRET_KEY partagée)."""
    custom = (settings.INVOICE_INTERNAL_API_KEY or "").strip()
    return custom or (settings.SECRET_KEY or "").strip()


if not settings.SECRET_KEY or len(settings.SECRET_KEY.strip()) < 32:
    raise RuntimeError("SECRET_KEY must be set in .env and be at least 32 characters.")
