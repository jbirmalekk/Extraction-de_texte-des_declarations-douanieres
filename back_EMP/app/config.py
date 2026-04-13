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

    # SMTP / Mailtrap
    SMTP_HOST: str = os.getenv("SMTP_HOST", "sandbox.smtp.mailtrap.io")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "no-reply@example.com")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    
    # OCR
    TESSERACT_PATH: str = os.getenv("TESSERACT_PATH", "")
    POPPLER_PATH: str = os.getenv("POPPLER_PATH", "")
    
    # CORS
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    # APP DEBUG & ENV
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    ENV: str = os.getenv("ENV", "development")
    
    class Config:
        env_file = ".env"


settings = Settings()
