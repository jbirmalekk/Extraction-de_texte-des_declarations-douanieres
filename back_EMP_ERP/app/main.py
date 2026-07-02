"""
Serveur S2 — API migration ERP (exemple localhost:8002).
Remplacez ERP_SERVICE_URL / OCR_API_URL en production par les URLs réelles.
"""
import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.config import settings
from app.database import init_db, test_connection
from app.routers.migration import router as migration_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("erp.main")

app = FastAPI(
    title="EMP ERP Migration API",
    description="Serveur S2 — récupère les données validées sur S1 et lance la migration ERP.",
    version="0.1.0",
)

cors_origins = [settings.FRONTEND_URL, "http://localhost:5173", "http://127.0.0.1:5173"]
if settings.CORS_ALLOWED_ORIGINS.strip():
    cors_origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(cors_origins)),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Internal-Service-Key"],
)

app.include_router(migration_router)


@app.on_event("startup")
def on_startup():
    try:
        init_db()
        logger.info("Base ERP_DB initialisée (%s)", settings.DB_NAME)
    except Exception as exc:
        logger.error("Init base ERP_DB échouée : %s", exc)


@app.get("/health")
def health():
    db_ok = False
    db_error = None
    try:
        db_ok = test_connection()
    except Exception as exc:
        db_error = str(exc)

    return {
        "status": "ok" if db_ok else "degraded",
        "service": "back_EMP_ERP",
        "ocr_api_url": settings.OCR_API_URL,
        "database": settings.DB_NAME,
        "database_ok": db_ok,
        "database_error": db_error,
        "env": settings.ENV,
    }
