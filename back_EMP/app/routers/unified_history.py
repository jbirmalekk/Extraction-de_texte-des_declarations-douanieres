"""
Historique unifié DUM + factures (lecture SQL directe sur la même base).
GET /api/history?type=dum|invoice|all&skip=0&limit=50
"""
from __future__ import annotations

import logging
from datetime import datetime

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.routers.dashboard import _build_history_payload, _load_documents_with_history
from app.services.invoice_list_service import list_invoice_history_items

logger = logging.getLogger("app.unified_history")

router = APIRouter(prefix="/api/history", tags=["Historique unifié"])


def _invoice_list_from_http(
    *,
    skip: int,
    limit: int,
    user: User,
    authorization: str | None,
) -> dict:
    """Repli HTTP vers back_EMP_Fact si la lecture SQL directe échoue."""
    base = (settings.INVOICE_API_URL or "").rstrip("/")
    if not base:
        return {"items": [], "total": 0, "skip": skip, "limit": limit, "source": "unavailable"}

    url = f"{base}/api/invoices"
    from app.routers.invoice_proxy import _internal_key

    headers = {
        "X-Internal-Service-Key": _internal_key(),
        "X-Authenticated-User-Id": str(user.id),
        "X-Authenticated-User-Role": (user.role or "user").strip().lower(),
        "X-Authenticated-Username": (user.username or "").strip(),
    }
    if authorization:
        headers["Authorization"] = authorization

    try:
        resp = requests.get(
            url,
            params={"skip": skip, "limit": limit},
            headers=headers,
            timeout=min(settings.INVOICE_API_TIMEOUT_SECONDS, 30),
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items") if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = []
        total = data.get("total", len(items)) if isinstance(data, dict) else len(items)
        mapped = [_map_invoice_history_item(i) for i in items]
        return {
            "items": mapped,
            "total": total,
            "skip": data.get("skip", skip) if isinstance(data, dict) else skip,
            "limit": data.get("limit", limit) if isinstance(data, dict) else limit,
            "source": "invoice_api",
        }
    except requests.RequestException as exc:
        logger.warning("invoice_http_fallback_failed err=%s", exc)
        return {
            "items": [],
            "total": 0,
            "skip": skip,
            "limit": limit,
            "source": "error",
            "error": str(exc),
        }


def _map_invoice_history_item(inv: dict) -> dict:
    created = inv.get("created_at") or inv.get("date_facture")
    return {
        "type": "invoice",
        "document_id": inv.get("id"),
        "document": inv.get("numero_facture") or inv.get("fichier_nom") or f"Facture #{inv.get('id')}",
        "numero_facture": inv.get("numero_facture"),
        "date_facture": inv.get("date_facture"),
        "fichier": inv.get("fichier_nom"),
        "owner": inv.get("owner") or inv.get("uploaded_by_username"),
        "date": created[:10] if isinstance(created, str) and len(created) >= 10 else None,
        "created_at": created,
        "status": inv.get("statut"),
        "statut_controle": inv.get("statut_controle"),
        "dum_document_id": inv.get("dum_document_id"),
        "numero_declaration_dum": inv.get("numero_declaration_dum"),
        "date_declaration_dum": inv.get("date_declaration_dum"),
        "net_pay": inv.get("net_pay"),
        "devise": inv.get("devise"),
        "compared_at": inv.get("compared_at"),
    }


def _invoice_list_for_history(
    db: Session,
    *,
    skip: int,
    limit: int,
    user: User,
    authorization: str | None,
) -> dict:
    try:
        items, total = list_invoice_history_items(
            db,
            user_id=user.id,
            role=user.role or "user",
            skip=skip,
            limit=limit,
        )
        return {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
            "source": "sql_direct",
        }
    except Exception as exc:
        logger.warning("invoice_sql_direct_failed err=%s — fallback HTTP", exc)
        return _invoice_list_from_http(
            skip=skip, limit=limit, user=user, authorization=authorization
        )


@router.get("")
def get_unified_history(
    type: str = Query("all", description="dum | invoice | all"),
    skip: int = 0,
    limit: int = Query(30, ge=1, le=200),
    authorization: str | None = Header(default=None, alias="Authorization"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc_type = (type or "all").strip().lower()
    if doc_type not in ("dum", "invoice", "all"):
        raise HTTPException(status_code=400, detail="type doit être dum, invoice ou all")

    now = datetime.utcnow()
    result: dict = {
        "type": doc_type,
        "skip": max(0, skip),
        "limit": limit,
        "items": [],
        "total": 0,
    }

    if doc_type in ("dum", "all"):
        if current_user.role == "admin":
            documents, total = _load_documents_with_history(db, skip=skip, limit=limit)
        else:
            documents, total = _load_documents_with_history(db, current_user, skip=skip, limit=limit)
        dum_payload = _build_history_payload(documents, now)
        for row in dum_payload.get("history", []):
            result["items"].append({**row, "type": "dum"})
        result["dum_total"] = total
        result["dum_stats"] = dum_payload.get("stats")

    if doc_type in ("invoice", "all"):
        inv_page = _invoice_list_for_history(
            db,
            skip=skip,
            limit=limit,
            user=current_user,
            authorization=authorization,
        )
        inv_items = inv_page.get("items", [])
        if doc_type == "all":
            result["items"].extend(inv_items)
            result["invoice_total"] = inv_page.get("total", 0)
            result["invoice_source"] = inv_page.get("source")
        else:
            result["items"] = inv_items
            result["total"] = inv_page.get("total", len(inv_items))
            result["invoice_source"] = inv_page.get("source")
            return result

    if doc_type == "all":
        result["items"].sort(
            key=lambda x: x.get("created_at") or x.get("date") or "",
            reverse=True,
        )
        result["total"] = (result.get("dum_total") or 0) + (result.get("invoice_total") or 0)
    else:
        result["total"] = result.get("dum_total", len(result["items"]))

    return result
