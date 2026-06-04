"""Lecture DUM (table documents) pour liaison 1–1 et comparaison facture."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.dum_document import DumDocument
from app.models.invoice import Invoice
from app.schemas.invoice import CompareDumBody


def parse_amount(raw: str | float | int | None) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip().replace("\u00a0", " ").replace(" ", "")
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_int_amount(raw: str | float | int | None) -> int | None:
    val = parse_amount(raw)
    if val is None:
        return None
    return int(round(val))


def get_dum_document(db: Session, document_id: int) -> DumDocument | None:
    return db.get(DumDocument, document_id)


def document_to_compare_body(doc: DumDocument) -> CompareDumBody:
    pfn = parse_amount(doc.montant_ptfn)
    return CompareDumBody(
        montant_pfn_dum=pfn,
        montant_declare_dum=pfn,
        devise_dum=(doc.devise or "").strip() or None,
        devise_declaree_dum=(doc.devise or "").strip() or None,
        numero_declaration_dum=(doc.numero_declaration or "").strip() or None,
        nombre_colis_dum=parse_int_amount(doc.nombre_colis),
        poids_net_kg_dum=parse_amount(doc.poids_net),
        incoterm_dum=(doc.mode_livraison or "").strip() or None,
    )


def merge_compare_body(db: Session, inv: Invoice, body: CompareDumBody) -> CompareDumBody:
    """Priorité : body explicite, sinon DUM liée (dum_document_id), sinon erreur plus tard."""
    dum_id = body.dum_document_id if body.dum_document_id is not None else inv.dum_document_id
    if not dum_id:
        return body

    doc = get_dum_document(db, dum_id)
    if not doc:
        return body

    from_db = document_to_compare_body(doc)
    return CompareDumBody(
        dum_document_id=dum_id,
        montant_pfn_dum=body.montant_pfn_dum if body.montant_pfn_dum is not None else from_db.montant_pfn_dum,
        montant_declare_dum=body.montant_declare_dum
        if body.montant_declare_dum is not None
        else from_db.montant_declare_dum,
        devise_dum=body.devise_dum or from_db.devise_dum,
        devise_declaree_dum=body.devise_declaree_dum or from_db.devise_declaree_dum,
        numero_declaration_dum=body.numero_declaration_dum or from_db.numero_declaration_dum,
        tolerance_abs=body.tolerance_abs,
        valeur_dinars_dum=body.valeur_dinars_dum,
        nombre_colis_dum=body.nombre_colis_dum if body.nombre_colis_dum is not None else from_db.nombre_colis_dum,
        poids_net_kg_dum=body.poids_net_kg_dum if body.poids_net_kg_dum is not None else from_db.poids_net_kg_dum,
        incoterm_dum=body.incoterm_dum or from_db.incoterm_dum,
    )


def assert_dum_available(db: Session, dum_document_id: int) -> DumDocument:
    doc = get_dum_document(db, dum_document_id)
    if not doc:
        raise ValueError(f"DUM document id={dum_document_id} introuvable")
    return doc


def find_invoice_linked_to_dum(db: Session, dum_document_id: int, exclude_invoice_id: int | None = None) -> Invoice | None:
    q = db.query(Invoice).filter(Invoice.dum_document_id == dum_document_id)
    if exclude_invoice_id is not None:
        q = q.filter(Invoice.id != exclude_invoice_id)
    return q.first()
