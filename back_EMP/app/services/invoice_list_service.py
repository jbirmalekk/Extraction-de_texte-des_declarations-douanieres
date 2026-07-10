"""Listes factures en lecture directe SQL (évite le proxy HTTP vers back_EMP_Fact)."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.invoice_read import InvoiceRead
from app.models.user import User


def _owner_labels(db: Session, rows: list[InvoiceRead]) -> dict[int, str]:
    user_ids = {r.uploaded_by_user_id for r in rows if r.uploaded_by_user_id is not None}
    if not user_ids:
        return {}
    users = db.query(User.id, User.username).filter(User.id.in_(user_ids)).all()
    return {uid: (name or f"Utilisateur #{uid}") for uid, name in users}


def _row_to_summary(inv: InvoiceRead, owner: str | None) -> dict:
    created = inv.created_at.isoformat() if inv.created_at else None
    return {
        "id": inv.id,
        "fichier_nom": inv.fichier_nom,
        "numero_facture": inv.numero_facture,
        "date_facture": inv.date_facture,
        "net_pay": inv.net_pay,
        "devise": inv.devise,
        "statut": inv.statut,
        "dum_document_id": inv.dum_document_id,
        "numero_declaration_dum": inv.numero_declaration_dum,
        "date_declaration_dum": inv.date_declaration_dum,
        "montant_declare_dum": inv.montant_declare_dum,
        "devise_declaree_dum": inv.devise_declaree_dum,
        "ecart_montant": inv.ecart_montant,
        "statut_controle": inv.statut_controle,
        "compared_at": inv.compared_at.isoformat() if inv.compared_at else None,
        "created_at": created,
        "owner": owner,
    }


def _row_to_history_item(inv: InvoiceRead, owner: str | None) -> dict:
    created = inv.created_at.isoformat() if inv.created_at else None
    label = inv.numero_facture or inv.fichier_nom or f"Facture #{inv.id}"
    return {
        "type": "invoice",
        "document_id": inv.id,
        "document": label,
        "numero_facture": inv.numero_facture,
        "date_facture": inv.date_facture,
        "fichier": inv.fichier_nom,
        "owner": owner,
        "date": created[:10] if isinstance(created, str) and len(created) >= 10 else None,
        "created_at": created,
        "status": inv.statut,
        "statut_controle": inv.statut_controle,
        "dum_document_id": inv.dum_document_id,
        "numero_declaration_dum": inv.numero_declaration_dum,
        "date_declaration_dum": inv.date_declaration_dum,
        "net_pay": inv.net_pay,
        "devise": inv.devise,
        "compared_at": inv.compared_at.isoformat() if inv.compared_at else None,
    }


def _base_query(db: Session, *, user_id: int, role: str, reports_only: bool = False):
    q = db.query(InvoiceRead)
    if (role or "").strip().lower() != "admin":
        q = q.filter(
            or_(
                InvoiceRead.uploaded_by_user_id == user_id,
                InvoiceRead.uploaded_by_user_id.is_(None),
            )
        )
    if reports_only:
        q = q.filter(
            or_(
                InvoiceRead.statut_controle.isnot(None),
                InvoiceRead.compared_at.isnot(None),
            )
        )
    return q


def list_invoice_summaries(
    db: Session,
    *,
    user_id: int,
    role: str,
    skip: int = 0,
    limit: int = 50,
    reports_only: bool = False,
) -> tuple[list[dict], int]:
    """Liste paginée légère (rapports ou historique factures)."""
    page_limit = max(1, min(limit, 200))
    page_skip = max(0, skip)
    base = _base_query(db, user_id=user_id, role=role, reports_only=reports_only)
    total = base.count()
    rows = (
        base.order_by(InvoiceRead.created_at.desc(), InvoiceRead.id.desc())
        .offset(page_skip)
        .limit(page_limit)
        .all()
    )
    owners = _owner_labels(db, rows)
    items = [
        _row_to_summary(r, owners.get(r.uploaded_by_user_id) if r.uploaded_by_user_id else None)
        for r in rows
    ]
    return items, total


def list_invoice_history_items(
    db: Session,
    *,
    user_id: int,
    role: str,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[dict], int]:
    """Lignes historique unifié (type invoice)."""
    page_limit = max(1, min(limit, 200))
    page_skip = max(0, skip)
    base = _base_query(db, user_id=user_id, role=role, reports_only=False)
    total = base.count()
    inv_rows = (
        base.order_by(InvoiceRead.created_at.desc(), InvoiceRead.id.desc())
        .offset(page_skip)
        .limit(page_limit)
        .all()
    )
    owners = _owner_labels(db, inv_rows)
    items = [
        _row_to_history_item(r, owners.get(r.uploaded_by_user_id) if r.uploaded_by_user_id else None)
        for r in inv_rows
    ]
    return items, total
