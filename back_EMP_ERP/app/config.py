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

    @property
    def internal_api_key(self) -> str:
        return (
            (self.ERP_INTERNAL_API_KEY or "").strip()
            or (self.INVOICE_INTERNAL_API_KEY or "").strip()
            or (self.SECRET_KEY or "").strip()
        )


settings = Settings()
