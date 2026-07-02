from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Serveur S2 — migration vers ERP (Uniges)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    OCR_API_URL: str = "http://localhost:8000"
    ERP_INTERNAL_API_KEY: str = ""
    INVOICE_INTERNAL_API_KEY: str = ""
    SECRET_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ALLOWED_ORIGINS: str = ""
    ENV: str = "development"
    DEBUG: bool = False

    # Base ERP locale (traçabilité migrations S2)
    DB_SERVER: str = "192.168.81.230\\SQLEXPRESS"
    DB_NAME: str = "EMP0206"
    DB_DRIVER: str = "ODBC Driver 18 for SQL Server"
    DB_TRUSTED_CONNECTION: str = "yes"
    DB_USER: str = "GMAO"
    DB_PASSWORD: str = "123456"
    DB_ENCRYPT: str = "no"

    @property
    def internal_api_key(self) -> str:
        return (
            (self.ERP_INTERNAL_API_KEY or "").strip()
            or (self.INVOICE_INTERNAL_API_KEY or "").strip()
            or (self.SECRET_KEY or "").strip()
        )


settings = Settings()
