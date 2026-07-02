"""Renomme erp_migration_logs -> X_Declaration_Facture (migration ponctuelle)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from sqlalchemy import text

from app.database.connection import engine, init_db

OLD = "erp_migration_logs"
NEW = "X_Declaration_Facture"


def main() -> int:
    with engine.connect() as conn:
        old_exists = conn.execute(
            text("SELECT 1 FROM sys.tables WHERE name = :name"),
            {"name": OLD},
        ).scalar()
        new_exists = conn.execute(
            text("SELECT 1 FROM sys.tables WHERE name = :name"),
            {"name": NEW},
        ).scalar()

    if old_exists and not new_exists:
        autocommit_engine = engine.execution_options(isolation_level="AUTOCOMMIT")
        with autocommit_engine.connect() as conn:
            conn.execute(text(f"EXEC sp_rename N'dbo.{OLD}', N'{NEW}'"))
        print(f"Table renommee : {OLD} -> {NEW}")
    elif new_exists:
        print(f"Table {NEW} deja presente")
    else:
        init_db()
        print(f"Table {NEW} creee")

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name FROM sys.tables WHERE name IN (:a, :b)"),
            {"a": OLD, "b": NEW},
        ).fetchall()
        print("Tables:", [r[0] for r in rows])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
