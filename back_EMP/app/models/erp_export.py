"""Enregistrement des payloads d'intégration ERP (serveur S1)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class ErpExport(Base):
    __tablename__ = "erp_exports"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(20), nullable=False)  # dum | invoice | dossier
    dum_document_id = Column(Integer, nullable=True, index=True)
    invoice_id = Column(Integer, nullable=True, index=True)
    reference = Column(String(120), nullable=True)
    payload_json = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="stored")  # stored | migration_ok | migration_failed
    migration_message = Column(Text, nullable=True)
    erp_reference = Column(String(120), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    migrated_at = Column(DateTime, nullable=True)
