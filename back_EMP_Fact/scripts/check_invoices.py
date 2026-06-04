"""Diagnostic: compte les factures en base."""
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.models.invoice import Invoice


def main() -> None:
    with engine.connect() as conn:
        tables = conn.execute(
            text(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                "WHERE TABLE_NAME LIKE 'invoice%'"
            )
        ).fetchall()
        print("tables:", [t[0] for t in tables])
        try:
            count = conn.execute(text("SELECT COUNT(*) FROM invoices")).scalar()
            print("SQL COUNT(*):", count)
            rows = conn.execute(
                text("SELECT TOP 10 id, fichier_nom, statut FROM invoices ORDER BY id DESC")
            ).fetchall()
            print("last rows:", rows)
        except Exception as exc:
            print("SQL error:", exc)

    db = SessionLocal()
    try:
        print("ORM count:", db.query(Invoice).count())
    finally:
        db.close()


if __name__ == "__main__":
    main()
