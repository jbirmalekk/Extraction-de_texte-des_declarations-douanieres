"""Lecture seule table invoices (même base SQL Server que back_EMP_Fact)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InvoiceRead(Base):
    """Sous-ensemble colonnes pour listes historique / rapports (pas de texte OCR)."""

    __tablename__ = "invoices"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fichier_nom: Mapped[str] = mapped_column(String(512))
    numero_facture: Mapped[str | None] = mapped_column(String(64), nullable=True)
    date_facture: Mapped[str | None] = mapped_column(String(32), nullable=True)
    devise: Mapped[str | None] = mapped_column(String(8), nullable=True)
    net_pay: Mapped[float | None] = mapped_column(Float, nullable=True)
    statut: Mapped[str] = mapped_column(String(32))
    uploaded_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dum_document_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_declaration_dum: Mapped[str | None] = mapped_column(String(32), nullable=True)
    date_declaration_dum: Mapped[str | None] = mapped_column(String(32), nullable=True)
    montant_declare_dum: Mapped[float | None] = mapped_column(Float, nullable=True)
    devise_declaree_dum: Mapped[str | None] = mapped_column(String(8), nullable=True)
    ecart_montant: Mapped[float | None] = mapped_column(Float, nullable=True)
    statut_controle: Mapped[str | None] = mapped_column(String(16), nullable=True)
    compared_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
