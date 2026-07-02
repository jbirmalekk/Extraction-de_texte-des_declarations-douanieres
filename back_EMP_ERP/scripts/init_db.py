"""
Crée les tables dans ERP_DB (SQL Server).

Usage (depuis back_EMP_ERP/) :
  python scripts/init_db.py
  python scripts/init_db.py --test-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.config import settings
from app.database.connection import ensure_database_exists, init_db, test_connection


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialiser la base ERP_DB")
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Tester la connexion sans créer les tables",
    )
    args = parser.parse_args()

    print(f"Serveur : {settings.DB_SERVER}")
    print(f"Base    : {settings.DB_NAME}")

    try:
        ensure_database_exists()
        print(f"Base {settings.DB_NAME} : OK (creee ou deja presente)")
    except Exception as exc:
        print(f"Creation base : ECHEC — {exc}")
        return 1

    try:
        test_connection()
        print("Connexion SQL Server : OK")
    except Exception as exc:
        print(f"Connexion SQL Server : ECHEC — {exc}")
        return 1

    if args.test_only:
        return 0

    try:
        init_db()
        print("Tables creees (ou deja existantes) : X_Declaration_Facture")
    except Exception as exc:
        print(f"Migration : ECHEC — {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
