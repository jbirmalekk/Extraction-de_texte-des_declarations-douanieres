"""
Database connection et configuration SQLAlchemy
Gère la connexion à SQL Server et les sessions
"""

from urllib.parse import quote_plus
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from app.config import settings

# ═══════════════════════════════════════════════════════════════
# BASE pour les modèles SQLAlchemy
# ═══════════════════════════════════════════════════════════════
Base = declarative_base()

# ═══════════════════════════════════════════════════════════════
# CONNECTION STRING SQL Server
# ═══════════════════════════════════════════════════════════════

if settings.DB_USER and settings.DB_PASSWORD:
    auth_part = f"UID={settings.DB_USER};PWD={settings.DB_PASSWORD};"
else:
    auth_part = f"Trusted_Connection={settings.DB_TRUSTED_CONNECTION};"

odbc_str = (
    f"DRIVER={{{settings.DB_DRIVER}}};"
    f"SERVER={settings.DB_SERVER};"
    f"DATABASE={settings.DB_NAME};"
    f"{auth_part}"
    f"Encrypt={settings.DB_ENCRYPT};"
    "TrustServerCertificate=yes;"
)
connection_string = f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}"

# Créer l'engine SQLAlchemy
engine = create_engine(
    connection_string,
    echo=settings.DEBUG,  # Afficher les requêtes SQL en debug
    pool_pre_ping=True,   # Vérifier connexion avant chaque request
    pool_size=10,
    max_overflow=20,
)

# ═══════════════════════════════════════════════════════════════
# SESSION FACTORY
# ═══════════════════════════════════════════════════════════════
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ═══════════════════════════════════════════════════════════════
# GET_DB DEPENDENCY (pour FastAPI)
# ═══════════════════════════════════════════════════════════════

def get_db() -> Iterator[Session]:
    """
    Dependency pour FastAPI.
    Fournit une session DB et s'assure qu'elle est fermée après la requête.
    
    Usage:
        @router.post("/ocr")
        async def extract_declaration(
            file: UploadFile = File(...),
            db: Session = Depends(get_db),  # ← Injection automatique
        ):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

# ═══════════════════════════════════════════════════════════════
# INIT_DB (créer les tables au startup)
# ═══════════════════════════════════════════════════════════════

def init_db():
    """
    Crée toutes les tables dans la base de données.
    Appelée au startup de l'application FastAPI.
    
    Utilise Base.metadata pour créer les tables correspondant
    aux modèles SQLAlchemy déclarés.
    """
    try:
        # Créer les tables si elles n'existent pas
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise

# ═══════════════════════════════════════════════════════════════
# TEST CONNECTION
# ═══════════════════════════════════════════════════════════════

def test_connection():
    """
    Test la connexion à la base de données.
    À utiliser pour vérifier que tout fonctionne.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
