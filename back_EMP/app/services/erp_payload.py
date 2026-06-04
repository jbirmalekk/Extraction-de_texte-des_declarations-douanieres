"""Construction du JSON d'intégration ERP à partir DUM + facture."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import Document
from app.routers.invoice_proxy import _internal_key


def _fetch_invoice_detail(invoice_id: int, user_id: int, user_role: str, username: str) -> dict | None:
    base = (settings.INVOICE_API_URL or "").rstrip("/")
    if not base:
        return None
    url = f"{base}/api/invoices/{invoice_id}"
    headers = {
        "X-Internal-Service-Key": _internal_key(),
        "X-Authenticated-User-Id": str(user_id),
        "X-Authenticated-User-Role": (user_role or "user").strip().lower(),
        "X-Authenticated-Username": (username or "").strip(),
    }
    try:
        resp = requests.get(url, headers=headers, timeout=settings.INVOICE_API_TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else None
    except requests.RequestException:
        return None


def _document_snapshot(doc: Document) -> dict[str, Any]:
    cols = {c.name: getattr(doc, c.name, None) for c in Document.__table__.columns}
    for key in ("created_at", "updated_at"):
        val = cols.get(key)
        if val is not None and hasattr(val, "isoformat"):
            cols[key] = val.isoformat()
    return cols


def build_erp_validation_payload(
    db: Session,
    *,
    kind: str,
    dum_document_id: int | None,
    invoice_id: int | None,
    reference: str | None,
    user_id: int,
    user_role: str,
    username: str,
) -> dict[str, Any]:
    dum_row = None
    if dum_document_id:
        dum_row = db.get(Document, dum_document_id)

    invoice_row = None
    if invoice_id:
        invoice_row = _fetch_invoice_detail(invoice_id, user_id, user_role, username)

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "kind": kind,
        "reference": reference,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "exported_by": {"user_id": user_id, "username": username, "role": user_role},
        "dum": _document_snapshot(dum_row) if dum_row else None,
        "invoice": invoice_row,
        "controle": None,
    }

    if invoice_row:
        payload["controle"] = {
            "statut_controle": invoice_row.get("statut_controle"),
            "ecart_montant": invoice_row.get("ecart_montant"),
            "ecart_commentaire": invoice_row.get("ecart_commentaire"),
            "compared_at": invoice_row.get("compared_at"),
            "montant_declare_dum": invoice_row.get("montant_declare_dum"),
            "numero_declaration_dum": invoice_row.get("numero_declaration_dum"),
            "date_declaration_dum": invoice_row.get("date_declaration_dum"),
        }

    return payload


def payload_to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)
