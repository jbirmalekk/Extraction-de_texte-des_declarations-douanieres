"""Lecture seule de la table documents (DUM) — même base SQL Server que back_EMP."""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DumDocument(Base):
    """Sous-ensemble des colonnes documents utilisées pour la comparaison facture."""

    __tablename__ = "documents"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    numero_declaration: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_declaration: Mapped[str | None] = mapped_column(String(20), nullable=True)
    devise: Mapped[str | None] = mapped_column(String(10), nullable=True)
    montant_ptfn: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nombre_colis: Mapped[str | None] = mapped_column(String(20), nullable=True)
    poids_net: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mode_livraison: Mapped[str | None] = mapped_column(String(20), nullable=True)
    dossier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fichier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    statut: Mapped[str | None] = mapped_column(String(50), nullable=True)
