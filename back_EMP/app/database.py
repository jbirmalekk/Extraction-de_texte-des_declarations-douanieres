"""
Database - Connexion SQLAlchemy vers SQL Server
Construit l'URL de connexion depuis les variables d'environnement
"""
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

Base = declarative_base()


def get_database_url() -> str:
    """
    Construit l'URL de connexion SQL Server depuis les variables d'environnement.
    Supporte Windows Authentication (Trusted_Connection) ou SQL Authentication.
    """
    if settings.DB_TRUSTED_CONNECTION.lower() in ("yes", "true", "1"):
        # Windows Authentication
        conn_str = (
            f"Driver={{{settings.DB_DRIVER}}};"
            f"Server={settings.DB_SERVER};"
            f"Database={settings.DB_NAME};"
            f"Trusted_Connection=yes;"
            f"Encrypt={settings.DB_ENCRYPT}"
        )
    else:
        # SQL Server Authentication
        conn_str = (
            f"Driver={{{settings.DB_DRIVER}}};"
            f"Server={settings.DB_SERVER};"
            f"Database={settings.DB_NAME};"
            f"UID={settings.DB_USER};"
            f"PWD={settings.DB_PASSWORD};"
            f"Encrypt={settings.DB_ENCRYPT}"
        )
    
    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(conn_str)


DATABASE_URL = get_database_url()

# Création de l'engine SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    echo=False,  # True pour debug SQL
    pool_pre_ping=True,  # Vérifier connexion avant utilisation
    pool_recycle=3600  # Recycler les connexions après 1h
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency pour obtenir une session de base de données.
    Utilisée dans les endpoints FastAPI avec Depends(get_db).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialise la base de données (crée les tables si elles n'existent pas).
    À appeler au démarrage de l'application.
    """
    Base.metadata.create_all(bind=engine)
