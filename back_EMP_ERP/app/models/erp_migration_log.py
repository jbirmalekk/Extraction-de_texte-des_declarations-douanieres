"""Journal des migrations ERP reçues depuis S1 (base ERP_DB)."""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class ErpMigrationLog(Base):
    __tablename__ = "X_Declaration_Facture"

    id = Column(Integer, primary_key=True, index=True)
    s1_export_id = Column(Integer, nullable=False, index=True)
    kind = Column(String(20), nullable=False)  # dum | invoice | dossier
    reference = Column(String(120), nullable=True)
    status = Column(String(32), nullable=False, default="pending")  # pending | migration_ok | migration_failed
    migration_message = Column(Text, nullable=True)
    erp_reference = Column(String(120), nullable=True)
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    migrated_at = Column(DateTime, nullable=True)
