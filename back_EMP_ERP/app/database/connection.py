"""Connexion SQL Server — base ERP_DB (serveur S2)."""

from __future__ import annotations

from typing import Iterator
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()

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

engine = create_engine(
    connection_string,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ensure_database_exists() -> None:
    """Crée ERP_DB sur le serveur si elle n'existe pas encore."""
    master_odbc = (
        f"DRIVER={{{settings.DB_DRIVER}}};"
        f"SERVER={settings.DB_SERVER};"
        f"DATABASE=master;"
        f"{auth_part}"
        f"Encrypt={settings.DB_ENCRYPT};"
        "TrustServerCertificate=yes;"
    )
    master_engine = create_engine(
        f"mssql+pyodbc:///?odbc_connect={quote_plus(master_odbc)}",
        pool_pre_ping=True,
        isolation_level="AUTOCOMMIT",
    )
    db_name = settings.DB_NAME.replace("]", "]]")
    with master_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM sys.databases WHERE name = :name"),
            {"name": settings.DB_NAME},
        ).scalar()
        if not exists:
            conn.execute(text(f"CREATE DATABASE [{db_name}]"))


def init_db() -> None:
    ensure_database_exists()
    # Import des modèles pour enregistrement dans Base.metadata
    from app.models import erp_migration_log  # noqa: F401

    Base.metadata.create_all(bind=engine)


def test_connection() -> bool:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
