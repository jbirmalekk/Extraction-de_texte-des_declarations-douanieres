"""
Compatibility layer for the canonical database package.

Canonical SQLAlchemy setup now lives in `app.database.connection`.
This module re-exports the same symbols so existing imports keep working.
"""

from .database.connection import Base, SessionLocal, engine, get_db, init_db, test_connection

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    "test_connection",
]
