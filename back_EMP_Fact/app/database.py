from __future__ import annotations

from pathlib import Path
from typing import Iterator
from urllib.parse import quote_plus

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.config import settings


class Base(DeclarativeBase):
    pass


def _build_connection_url() -> str:
    if settings.DATABASE_URL.strip():
        return settings.DATABASE_URL.strip()

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
    return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}"


def _ensure_sqlite_dir(url: str) -> None:
    if url.startswith("sqlite:///./") or url.startswith("sqlite:///"):
        raw = url.replace("sqlite:///", "", 1)
        if raw.startswith("./"):
            path = Path(raw[2:])
            path.parent.mkdir(parents=True, exist_ok=True)


connection_url = _build_connection_url()
_ensure_sqlite_dir(connection_url)

connect_args = {}
if connection_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    connection_url,
    connect_args=connect_args,
    echo=settings.DEBUG,
    pool_pre_ping=not connection_url.startswith("sqlite"),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sql_type(mssql: str, sqlite: str = "TEXT") -> str:
    return sqlite if connection_url.startswith("sqlite") else mssql


def _migrate_table_columns(table: str, additions: tuple[tuple[str, str, str], ...]) -> None:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    with engine.begin() as conn:
        for name, mssql_type, sqlite_type in additions:
            if name not in cols:
                sql_type = _sql_type(mssql_type, sqlite_type)
                conn.execute(text(f"ALTER TABLE {table} ADD {name} {sql_type}"))


def _migrate_invoices() -> None:
    _migrate_table_columns(
        "invoices",
        (
            ("dum_document_id", "INT NULL", "INTEGER"),
            ("dossier", "NVARCHAR(1024) NULL", "TEXT"),
            ("uploaded_by_user_id", "INT NULL", "INTEGER"),
            ("compared_at", "DATETIME NULL", "DATETIME"),
            ("extraction_warnings_json", "NVARCHAR(MAX) NULL", "TEXT"),
            ("field_confidence_json", "NVARCHAR(MAX) NULL", "TEXT"),
            ("numero_declaration_dum", "NVARCHAR(32) NULL", "TEXT"),
            ("date_declaration_dum", "NVARCHAR(32) NULL", "TEXT"),
            ("montant_declare_dum", "FLOAT NULL", "REAL"),
            ("devise_declaree_dum", "NVARCHAR(8) NULL", "TEXT"),
            ("ecart_montant", "FLOAT NULL", "REAL"),
            ("ecart_commentaire", "NVARCHAR(512) NULL", "TEXT"),
            ("statut_controle", "NVARCHAR(16) NULL", "TEXT"),
            ("controle_anomalies_json", "NVARCHAR(MAX) NULL", "TEXT"),
        ),
    )


def init_db() -> None:
    from app.models.dum_document import DumDocument  # noqa: F401
    from app.models.invoice import Invoice, InvoiceLine  # noqa: F401
    from app.models.invoice_upload_trace import InvoiceUploadTrace  # noqa: F401

    _ = DumDocument, Invoice, InvoiceLine, InvoiceUploadTrace

    for table in (
        Invoice.__table__,
        InvoiceLine.__table__,
        InvoiceUploadTrace.__table__,
    ):
        table.create(bind=engine, checkfirst=True)

    _migrate_invoices()
    _ensure_invoice_foreign_keys()


def _fk_exists(insp, table: str, name: str) -> bool:
    try:
        return name in {fk.get("name") for fk in insp.get_foreign_keys(table)}
    except Exception:
        return False


def _ensure_invoice_foreign_keys() -> None:
    """FK logiques vers documents/users (tables déjà gérées par back_EMP)."""
    if connection_url.startswith("sqlite"):
        return
    insp = inspect(engine)
    if "invoices" not in insp.get_table_names():
        return
    statements = []
    if not _fk_exists(insp, "invoices", "FK_invoices_documents"):
        statements.append(
            "ALTER TABLE invoices ADD CONSTRAINT FK_invoices_documents "
            "FOREIGN KEY (dum_document_id) REFERENCES documents(id)"
        )
    if not _fk_exists(insp, "invoices", "FK_invoices_users"):
        statements.append(
            "ALTER TABLE invoices ADD CONSTRAINT FK_invoices_users "
            "FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id)"
        )
    if "invoice_upload_traces" in insp.get_table_names() and not _fk_exists(
        insp, "invoice_upload_traces", "FK_invoice_traces_users"
    ):
        statements.append(
            "ALTER TABLE invoice_upload_traces ADD CONSTRAINT FK_invoice_traces_users "
            "FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id)"
        )
    if not statements:
        return
    with engine.begin() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception as exc:
                # Déjà présent ou droits insuffisants — ne bloque pas le démarrage
                import logging

                logging.getLogger("invoice_fact.db").warning("FK skip: %s (%s)", stmt, exc)
