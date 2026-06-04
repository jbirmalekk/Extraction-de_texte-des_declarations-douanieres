"""
Main - Application FastAPI principale
point d'entrée de l'API
"""
import logging
import time
import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy import text

from .config import settings
from .database import init_db, SessionLocal
from .routers import auth
# Importer les modèles AVANT init_db pour que SQLAlchemy les connaisse
from app.models.document import Document, Taxe, Article
from app.models.erp_export import ErpExport
from app.models.user import User, RevokedToken

from .routers.dashboard import router as dashboard_router
from .routers.unified_history import router as unified_history_router
from .routers.invoice_proxy import router as invoice_proxy_router
from .routers.erp_export import router as erp_export_router
from app.routers.ocr import router as ocr_router
# Charger les variables d'environnement
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("app.main")

# Créer l'application FastAPI
app = FastAPI(
    title="OCR Extraction API",
    description="API pour l'extraction automatique de données depuis des documents PDF/scannés",
    version="1.0.0"
)

cors_origins = [settings.FRONTEND_URL, "http://localhost:5173", "http://127.0.0.1:5173"]
if settings.CORS_ALLOWED_ORIGINS.strip():
    cors_origins = [origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]
cors_origins = list(dict.fromkeys(cors_origins))


def _cors_headers_for_request(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin")
    if origin and origin in cors_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return {}

# Configuration CORS pour permettre au frontend d'accéder à l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    # Must list every custom header the browser sends (preflight checks each one).
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Client-PC-Name",
        "X-Internal-Service-Key",
    ],
)

# Inclure les routers
app.include_router(auth.router)
app.include_router(dashboard_router)
app.include_router(unified_history_router)
app.include_router(invoice_proxy_router)
app.include_router(erp_export_router)
app.include_router(ocr_router)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started = time.time()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = int((time.time() - started) * 1000)
        logger.exception(
            "request_failed request_id=%s method=%s path=%s elapsed_ms=%s",
            request_id,
            request.method,
            request.url.path,
            elapsed_ms,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "request_id": request_id,
            },
            headers=_cors_headers_for_request(request),
        )

    elapsed_ms = int((time.time() - started) * 1000)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_done request_id=%s method=%s path=%s status=%s elapsed_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_with_cors(request: Request, exc: StarletteHTTPException):
    response = await http_exception_handler(request, exc)
    for key, value in _cors_headers_for_request(request).items():
        response.headers[key] = value
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return await http_exception_with_cors(request, exc)
    logger.exception(
        "unhandled_exception method=%s path=%s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "message": "Erreur interne du serveur.",
                "error": str(exc)[:500],
            },
        },
        headers=_cors_headers_for_request(request),
    )


# Event startup : initialiser la base de données
@app.on_event("startup")
def on_startup():
    """
    Événement exécuté au démarrage de l'application.
    Initialise la base de données (crée les tables si elles n'existent pas).
    """
    print("🚀 Starting application...")
    print(f"📊 Database: {settings.DB_SERVER}/{settings.DB_NAME}")
    init_db()
    print("✅ Database initialized")

    try:
        import subprocess
        from app.config import settings as cfg

        tesseract_cmd = cfg.TESSERACT_PATH or "tesseract"
        subprocess.run(
            [tesseract_cmd, "--version"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        print(f"✅ Tesseract OK ({tesseract_cmd})")
    except Exception as exc:
        print(f"⚠️  Tesseract indisponible — les extractions OCR echoueront: {exc}")


# Endpoint racine pour vérifier que l'API fonctionne
@app.get("/", tags=["Root"])
def read_root():
    """
    Endpoint racine - Vérifier que l'API est en ligne
    """
    return {
        "message": "OCR Extraction API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }


# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    """
    Endpoint pour vérifier la santé de l'API
    """
    db_ok = False
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    finally:
        db.close()

    ocr_ok = False
    ocr_detail = "unknown"
    try:
        import shutil
        import subprocess

        tesseract_cmd = shutil.which("tesseract") or settings.TESSERACT_PATH
        if tesseract_cmd:
            subprocess.run(
                [tesseract_cmd, "--version"],
                capture_output=True,
                check=True,
                timeout=8,
            )
            ocr_ok = True
            ocr_detail = "tesseract_available"
        else:
            ocr_detail = "tesseract_not_found"
    except Exception as exc:
        ocr_detail = f"tesseract_error:{str(exc)[:120]}"

    status = "healthy" if db_ok and ocr_ok else "degraded"
    return {
        "status": status,
        "database": "connected" if db_ok else "disconnected",
        "ocr": ocr_detail,
        "ocr_ready": ocr_ok,
    }
