"""
Intégration ERP — serveur S1 (OCR).
POST /api/erp/validation-data  — enregistre le JSON en base
GET  /api/erp/validation-data/{export_id} — lecture (S2 migration)
Alias GET /api/get-validation-data/{export_id}
"""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.erp_export import ErpExport
from app.models.user import User
from app.routers.auth import get_current_user
from app.routers.invoice_proxy import _internal_key
from app.services.erp.erp_payload import build_erp_validation_payload, payload_to_json

router = APIRouter(tags=["ERP — export S1"])


class ErpValidationDataCreate(BaseModel):
    kind: str = Field(..., description="dum | invoice | dossier")
    dum_document_id: int | None = None
    invoice_id: int | None = None
    reference: str | None = None


class ErpValidationDataOut(BaseModel):
    export_id: int
    kind: str
    status: str
    reference: str | None
    payload: dict


class ErpMigrationStatusUpdate(BaseModel):
    status: str = Field(..., description="migration_ok | migration_failed")
    message: str | None = None
    erp_reference: str | None = None


def _verify_internal_key(x_internal_service_key: str | None = Header(default=None)) -> None:
    expected = _internal_key()
    if not x_internal_service_key or x_internal_service_key.strip() != expected:
        raise HTTPException(status_code=403, detail="Clé interne ERP invalide.")


@router.post("/api/erp/validation-data", response_model=ErpValidationDataOut)
@router.post("/api/get-validation-data", response_model=ErpValidationDataOut, include_in_schema=False)
def create_erp_validation_data(
    body: ErpValidationDataCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kind = (body.kind or "").strip().lower()
    if kind not in ("dum", "invoice", "dossier"):
        raise HTTPException(status_code=400, detail="kind doit être dum, invoice ou dossier.")

    if kind == "dum" and not body.dum_document_id:
        raise HTTPException(status_code=400, detail="dum_document_id requis pour kind=dum.")
    if kind == "invoice" and not body.invoice_id:
        raise HTTPException(status_code=400, detail="invoice_id requis pour kind=invoice.")
    if kind == "dossier" and (not body.dum_document_id or not body.invoice_id):
        raise HTTPException(
            status_code=400,
            detail="dum_document_id et invoice_id requis pour kind=dossier.",
        )

    payload = build_erp_validation_payload(
        db,
        kind=kind,
        dum_document_id=body.dum_document_id,
        invoice_id=body.invoice_id,
        reference=body.reference,
        user_id=current_user.id,
        user_role=current_user.role or "user",
        username=current_user.username or "",
    )

    row = ErpExport(
        kind=kind,
        dum_document_id=body.dum_document_id,
        invoice_id=body.invoice_id,
        reference=body.reference,
        payload_json=payload_to_json(payload),
        status="stored",
        created_by_user_id=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return ErpValidationDataOut(
        export_id=row.id,
        kind=row.kind,
        status=row.status,
        reference=row.reference,
        payload=payload,
    )


@router.get("/api/erp/validation-data/{export_id}")
@router.get("/api/get-validation-data/{export_id}")
def get_erp_validation_data(
    export_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_internal_key),
):
    row = db.get(ErpExport, export_id)
    if not row:
        raise HTTPException(status_code=404, detail="Export ERP introuvable.")
    try:
        payload = json.loads(row.payload_json)
    except json.JSONDecodeError:
        payload = {"raw": row.payload_json}

    return {
        "export_id": row.id,
        "kind": row.kind,
        "status": row.status,
        "reference": row.reference,
        "dum_document_id": row.dum_document_id,
        "invoice_id": row.invoice_id,
        "payload": payload,
        "migration_message": row.migration_message,
        "erp_reference": row.erp_reference,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "migrated_at": row.migrated_at.isoformat() if row.migrated_at else None,
    }


@router.patch("/api/erp/validation-data/{export_id}/migration-status")
def update_migration_status(
    export_id: int,
    body: ErpMigrationStatusUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_internal_key),
):
    row = db.get(ErpExport, export_id)
    if not row:
        raise HTTPException(status_code=404, detail="Export ERP introuvable.")

    status = (body.status or "").strip().lower()
    if status not in ("migration_ok", "migration_failed"):
        raise HTTPException(status_code=400, detail="status invalide.")

    row.status = status
    row.migration_message = body.message
    row.erp_reference = body.erp_reference
    row.migrated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)

    return {
        "export_id": row.id,
        "status": row.status,
        "erp_reference": row.erp_reference,
        "migrated_at": row.migrated_at.isoformat() if row.migrated_at else None,
    }
