"""
Main - Application FastAPI principale
point d'entrée de l'API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .config import settings
from .database import init_db
from .routers import auth
# Importer les modèles AVANT init_db pour que SQLAlchemy les connaisse
from app.models.document import Document, Taxe, Article

from app.routers.ocr import router as ocr_router
# Charger les variables d'environnement
load_dotenv()

# Créer l'application FastAPI
app = FastAPI(
    title="OCR Extraction API",
    description="API pour l'extraction automatique de données depuis des documents PDF/scannés",
    version="1.0.0"
)

# Configuration CORS pour permettre au frontend d'accéder à l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173"],  # URLs autorisées
    allow_credentials=True,
    allow_methods=["*"],  # Autoriser toutes les méthodes (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Autoriser tous les headers
)

# Inclure les routers
app.include_router(auth.router)
app.include_router(ocr_router)

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
    return {
        "status": "healthy",
        "database": "connected"
    }
