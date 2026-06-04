from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class InvoiceLineOut(BaseModel):
    id: int | None = None
    line_order: int = 0
    reference: str | None = None
    designation: str | None = None
    quantite: float | None = None
    prix_unitaire: float | None = None
    montant_ligne: float | None = None
    devise_ligne: str | None = None


class InvoiceExtractResult(BaseModel):
    """Payload renvoyé après extraction (avant ou après persistance)."""

    numero_facture: str | None = None
    date_facture: str | None = None
    devise: str | None = None
    client_code: str | None = None
    client_nom: str | None = None
    client_pays: str | None = None
    client_matricule_fiscal: str | None = None
    adresse_facturation: str | None = None
    adresse_expedition: str | None = None
    adresse_livraison: str | None = None
    montant_brut: float | None = None
    montant_remise: float | None = None
    montant_ht_ou_amount: float | None = None
    montant_ttc: float | None = None
    net_pay: float | None = None
    nombre_colis: int | None = None
    poids_brut_kg: float | None = None
    poids_net_kg: float | None = None
    incoterm: str | None = None
    mode_transport_libelle: str | None = None
    conditions_paiement: str | None = None
    notes_reference: str | None = None
    lines: list[InvoiceLineOut] = Field(default_factory=list)
    texte_brut_extrait: str | None = None
    extraction_warnings: list[str] = Field(default_factory=list)
    field_confidence: dict[str, float] = Field(default_factory=dict)


class InvoiceUpdate(BaseModel):
    """Correction manuelle côté UI."""

    numero_facture: str | None = None
    date_facture: str | None = None
    devise: str | None = None
    client_code: str | None = None
    client_nom: str | None = None
    client_pays: str | None = None
    client_matricule_fiscal: str | None = None
    adresse_facturation: str | None = None
    adresse_expedition: str | None = None
    adresse_livraison: str | None = None
    montant_brut: float | None = None
    montant_remise: float | None = None
    montant_ht_ou_amount: float | None = None
    montant_ttc: float | None = None
    net_pay: float | None = None
    nombre_colis: int | None = None
    poids_brut_kg: float | None = None
    poids_net_kg: float | None = None
    incoterm: str | None = None
    mode_transport_libelle: str | None = None
    conditions_paiement: str | None = None
    notes_reference: str | None = None
    statut: str | None = None
    lines: list[InvoiceLineOut] | None = None


class DumAnomalyOut(BaseModel):
    code: str
    severity: str
    message: str
    facture_value: str | None = None
    dum_value: str | None = None


class StorageOut(BaseModel):
    provider: str
    nextcloud_path: str | None = None
    nextcloud_url: str | None = None
    nextcloud_etag: str | None = None
    fallback_reason: str | None = None
    error: str | None = None


class LinkDumBody(BaseModel):
    """Liaison 1–1 facture → documents.id (DUM)."""

    dum_document_id: int = Field(..., description="Id du document DUM (table documents)")


class CompareDumBody(BaseModel):
    """Comparaison principale : NET PAY facture ↔ PFN article (montant PTFN) DUM."""

    dum_document_id: int | None = Field(
        None,
        description="Si renseigné, charge PFN/devise/colis depuis la DUM en base (priorité aux champs explicites).",
    )
    montant_pfn_dum: float | None = Field(
        None,
        description="PFN de l'article / montant PTFN (devise facturation DUM)",
    )
    montant_declare_dum: float | None = Field(
        None,
        description="Alias historique — traité comme montant_pfn_dum si celui-ci est absent",
    )
    devise_dum: str | None = None
    devise_declaree_dum: str | None = None
    numero_declaration_dum: str | None = None
    tolerance_abs: float = 0.01
    valeur_dinars_dum: float | None = Field(None, description="Contrôle informatif TND (non comparé au NET PAY)")
    nombre_colis_dum: int | None = None
    poids_net_kg_dum: float | None = None
    incoterm_dum: str | None = None


class InvoiceListPage(BaseModel):
    """Liste paginée des factures."""

    items: list["InvoiceListItem"] = Field(default_factory=list)
    total: int = 0
    skip: int = 0
    limit: int = 50


class InvoiceListItem(BaseModel):
    """Résumé pour sélection dans la réconciliation DUM ↔ facture."""

    id: int
    fichier_nom: str = ""
    numero_facture: str | None = None
    date_facture: str | None = None
    net_pay: float | None = None
    devise: str | None = None
    statut: str = "extracted"
    dum_document_id: int | None = None
    numero_declaration_dum: str | None = None
    statut_controle: str | None = None
    compared_at: datetime | None = None
    created_at: datetime | None = None
    owner: str | None = None

    class Config:
        from_attributes = True


class BulkDeleteIds(BaseModel):
    ids: list[int] = Field(..., min_length=1)


class InvoiceOut(InvoiceExtractResult):
    id: int
    fichier_nom: str
    content_type: str | None = None
    statut: str = "extracted"
    dossier: str | None = None
    uploaded_by_user_id: int | None = None
    dum_document_id: int | None = None
    compared_at: datetime | None = None
    storage: StorageOut | None = None
    numero_declaration_dum: str | None = None
    montant_declare_dum: float | None = None
    devise_declaree_dum: str | None = None
    ecart_montant: float | None = None
    ecart_commentaire: str | None = None
    statut_controle: str | None = None
    controle_anomalies: list[DumAnomalyOut] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
