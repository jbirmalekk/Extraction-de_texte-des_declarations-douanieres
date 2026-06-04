"""
API microservice factures fournisseurs — extraction, persistance, comparaison DUM.
"""
import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.config import settings
from app.database import init_db
from app.routers.invoices import router as invoices_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("invoice_fact.main")

app = FastAPI(title="EMP Facture API", version="0.1.0")

cors_origins = [settings.FRONTEND_URL, "http://localhost:5173"]
if settings.CORS_ALLOWED_ORIGINS.strip():
    cors_origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Client-PC-Name",
        "X-Internal-Service-Key",
        "X-Authenticated-User-Id",
        "X-Authenticated-User-Role",
        "X-Authenticated-Username",
    ],
)

app.include_router(invoices_router)


@app.on_event("startup")
def startup():
    Path("data").mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info(
        "DB ready (%s) | CORS origins=%s",
        settings.DB_NAME or settings.DATABASE_URL or "sqlserver",
        cors_origins,
    )


@app.get("/health")
def health():
    ocr_ok = False
    ocr_detail = "unknown"
    try:
        import shutil
        import subprocess

        cmd = (settings.TESSERACT_PATH or "").strip() or shutil.which("tesseract")
        if cmd:
            subprocess.run([cmd, "--version"], capture_output=True, check=True, timeout=8)
            ocr_ok = True
            ocr_detail = "tesseract_available"
        else:
            ocr_detail = "tesseract_not_found"
    except Exception as exc:
        ocr_detail = f"tesseract_error:{str(exc)[:120]}"
    return {
        "status": "ok" if ocr_ok else "degraded",
        "service": "invoice-fact",
        "ocr": ocr_detail,
        "ocr_ready": ocr_ok,
    }
