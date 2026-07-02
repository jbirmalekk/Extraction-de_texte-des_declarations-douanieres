"""
Serveur S2 — migration ERP.
POST /api/migration : récupère le JSON sur S1 puis exécute la migration (simulation dev).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.erp_migration_log import ErpMigrationLog

logger = logging.getLogger("erp.migration")

router = APIRouter(prefix="/api", tags=["Migration ERP"])


class MigrationRequest(BaseModel):
    export_id: int = Field(..., gt=0)


class MigrationResponse(BaseModel):
    success: bool
    export_id: int
    message: str
    erp_reference: str | None = None
    kind: str | None = None
    reference: str | None = None


def _internal_key() -> str:
    key = settings.internal_api_key
    if key:
        return key
    raise RuntimeError(
        "ERP_INTERNAL_API_KEY (ou INVOICE_INTERNAL_API_KEY / SECRET_KEY) requis pour appeler S1."
    )


def _fetch_validation_data_from_s1(export_id: int) -> dict:
    base = settings.OCR_API_URL.rstrip("/")
    url = f"{base}/api/erp/validation-data/{export_id}"
    headers = {"X-Internal-Service-Key": _internal_key()}
    try:
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("detail", "")
        except Exception:
            detail = exc.response.text if exc.response is not None else str(exc)
        raise HTTPException(
            status_code=exc.response.status_code if exc.response is not None else 502,
            detail=detail or "Impossible de récupérer les données sur le serveur OCR (S1).",
        ) from exc
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Serveur OCR (S1) injoignable : {exc}",
        ) from exc


def _notify_s1_migration_result(
    export_id: int,
    *,
    success: bool,
    message: str,
    erp_reference: str | None,
) -> None:
    base = settings.OCR_API_URL.rstrip("/")
    url = f"{base}/api/erp/validation-data/{export_id}/migration-status"
    headers = {
        "X-Internal-Service-Key": _internal_key(),
        "Content-Type": "application/json",
    }
    body = {
        "status": "migration_ok" if success else "migration_failed",
        "message": message,
        "erp_reference": erp_reference,
    }
    try:
        requests.patch(url, json=body, headers=headers, timeout=30)
    except requests.RequestException:
        logger.warning("Mise à jour statut migration S1 échouée pour export_id=%s", export_id)


def _run_erp_migration(export_bundle: dict) -> tuple[bool, str, str | None]:
    """
    Point d'extension : brancher ici l'API Uniges / ERP réelle.
    En dev : simulation réussie si payload présent.
    """
    payload = export_bundle.get("payload")
    if not payload:
        return False, "Payload ERP vide.", None

    export_id = export_bundle.get("export_id")
    kind = export_bundle.get("kind", "dossier")
    ref = export_bundle.get("reference") or payload.get("reference") or f"EXP-{export_id}"
    erp_ref = f"UNIGES-{kind.upper()}-{export_id}-{datetime.utcnow().strftime('%Y%m%d')}"
    logger.info("Migration ERP simulée OK export_id=%s kind=%s ref=%s", export_id, kind, ref)
    return True, f"Migration ERP simulée réussie ({ref}).", erp_ref


def _persist_migration_log(
    db: Session,
    *,
    export_id: int,
    bundle: dict,
    success: bool,
    message: str,
    erp_reference: str | None,
) -> None:
    now = datetime.utcnow()
    row = ErpMigrationLog(
        s1_export_id=export_id,
        kind=str(bundle.get("kind") or "dossier"),
        reference=bundle.get("reference"),
        status="migration_ok" if success else "migration_failed",
        migration_message=message,
        erp_reference=erp_reference,
        payload_json=json.dumps(bundle.get("payload") or {}, ensure_ascii=False),
        migrated_at=now if success else None,
    )
    db.add(row)
    db.commit()


@router.post("/migration", response_model=MigrationResponse)
def migrate_to_erp(body: MigrationRequest, db: Session = Depends(get_db)):
    bundle = _fetch_validation_data_from_s1(body.export_id)
    success, message, erp_reference = _run_erp_migration(bundle)
    try:
        _persist_migration_log(
            db,
            export_id=body.export_id,
            bundle=bundle,
            success=success,
            message=message,
            erp_reference=erp_reference,
        )
    except Exception:
        logger.exception("Échec écriture journal ERP pour export_id=%s", body.export_id)
        db.rollback()

    _notify_s1_migration_result(
        body.export_id,
        success=success,
        message=message,
        erp_reference=erp_reference,
    )
    if not success:
        raise HTTPException(status_code=422, detail=message)

    return MigrationResponse(
        success=True,
        export_id=body.export_id,
        message=message,
        erp_reference=erp_reference,
        kind=bundle.get("kind"),
        reference=bundle.get("reference"),
    )
