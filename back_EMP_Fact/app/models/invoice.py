from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Invoice(Base):
    """En-tête facture fournisseur (ex. Export Invoice EMP)."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fichier_nom: Mapped[str] = mapped_column(String(512), default="")
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    dossier: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    uploaded_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    # Unicité 1–1 DUM/facture uniquement quand lié (index filtré en migration SQL Server).
    dum_document_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    numero_facture: Mapped[str | None] = mapped_column(String(64), nullable=True)
    date_facture: Mapped[str | None] = mapped_column(String(32), nullable=True)
    devise: Mapped[str | None] = mapped_column(String(8), nullable=True)

    client_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    client_nom: Mapped[str | None] = mapped_column(String(512), nullable=True)
    client_pays: Mapped[str | None] = mapped_column(String(128), nullable=True)
    client_matricule_fiscal: Mapped[str | None] = mapped_column(String(128), nullable=True)
    adresse_facturation: Mapped[str | None] = mapped_column(Text, nullable=True)
    adresse_expedition: Mapped[str | None] = mapped_column(Text, nullable=True)
    adresse_livraison: Mapped[str | None] = mapped_column(Text, nullable=True)

    montant_brut: Mapped[float | None] = mapped_column(Float, nullable=True)
    montant_remise: Mapped[float | None] = mapped_column(Float, nullable=True)
    montant_ht_ou_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    montant_ttc: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_pay: Mapped[float | None] = mapped_column(Float, nullable=True)

    nombre_colis: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poids_brut_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    poids_net_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    incoterm: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mode_transport_libelle: Mapped[str | None] = mapped_column(String(128), nullable=True)
    conditions_paiement: Mapped[str | None] = mapped_column(String(256), nullable=True)
    notes_reference: Mapped[str | None] = mapped_column(Text, nullable=True)

    texte_brut_extrait: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_warnings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_confidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    statut: Mapped[str] = mapped_column(String(32), default="extracted")

    numero_declaration_dum: Mapped[str | None] = mapped_column(String(32), nullable=True)
    date_declaration_dum: Mapped[str | None] = mapped_column(String(32), nullable=True)
    montant_declare_dum: Mapped[float | None] = mapped_column(Float, nullable=True)
    devise_declaree_dum: Mapped[str | None] = mapped_column(String(8), nullable=True)
    ecart_montant: Mapped[float | None] = mapped_column(Float, nullable=True)
    ecart_commentaire: Mapped[str | None] = mapped_column(String(512), nullable=True)
    statut_controle: Mapped[str | None] = mapped_column(String(16), nullable=True)
    controle_anomalies_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    compared_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=lambda: datetime.utcnow()
    )

    lines: Mapped[list["InvoiceLine"]] = relationship(
        "InvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.line_order",
    )
    upload_traces: Mapped[list["InvoiceUploadTrace"]] = relationship(
        "InvoiceUploadTrace",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )


class InvoiceLine(Base):
    """Ligne article facture (référence, désignation, qté, PU, montant)."""

    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), index=True)
    line_order: Mapped[int] = mapped_column(Integer, default=0)

    reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    designation: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantite: Mapped[float | None] = mapped_column(Float, nullable=True)
    prix_unitaire: Mapped[float | None] = mapped_column(Float, nullable=True)
    montant_ligne: Mapped[float | None] = mapped_column(Float, nullable=True)
    devise_ligne: Mapped[str | None] = mapped_column(String(8), nullable=True)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="lines")


# Enregistre la table de traçabilité pour la relation upload_traces
from app.models.invoice_upload_trace import InvoiceUploadTrace  # noqa: E402, F401
