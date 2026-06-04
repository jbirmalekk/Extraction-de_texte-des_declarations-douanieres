from __future__ import annotations

import json
import logging
from datetime import datetime

from typing import Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, Response, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.deps import AuthUser, assert_invoice_access, get_current_user
from app.database import get_db
from app.models.dum_document import DumDocument
from app.models.invoice import Invoice, InvoiceLine
from app.models.invoice_upload_trace import InvoiceUploadTrace
from app.models.user_ref import UserRef
from app.schemas.invoice import (
    BulkDeleteIds,
    CompareDumBody,
    DumAnomalyOut,
    InvoiceExtractResult,
    InvoiceLineOut,
    InvoiceListItem,
    InvoiceListPage,
    InvoiceOut,
    InvoiceUpdate,
    LinkDumBody,
    StorageOut,
)
from app.services.dum_lookup import (
    assert_dum_available,
    document_to_compare_body,
    find_invoice_linked_to_dum,
    merge_compare_body,
    release_dum_from_other_invoices,
)
from app.services.invoice_compare import compare_invoice_with_dum
from app.services.invoice_extract import extract_invoice_from_bytes
from app.services.invoice_file_storage import (
    delete_local_invoice_file,
    find_local_invoice_by_id,
    is_local_dossier,
    read_local_invoice_file,
    save_local_invoice_file,
)
from app.services.nextcloud_storage import (
    NextcloudUploadError,
    download_file_from_nextcloud,
    upload_file_to_nextcloud,
)

router = APIRouter(prefix="/api/invoices", tags=["invoices"])
logger = logging.getLogger(__name__)

_ALLOWED = {"application/pdf", "image/png", "image/jpeg", "image/jpg"}


def _loads_json(raw: str | None, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


def _dumps_json(value) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _line_payload_dict(lo) -> dict:
    """Normalise une ligne (Pydantic, dict) après model_dump ou JSON client."""
    if isinstance(lo, dict):
        return lo
    if hasattr(lo, "model_dump"):
        return lo.model_dump()
    return {
        "line_order": getattr(lo, "line_order", None),
        "reference": getattr(lo, "reference", None),
        "designation": getattr(lo, "designation", None),
        "quantite": getattr(lo, "quantite", None),
        "prix_unitaire": getattr(lo, "prix_unitaire", None),
        "montant_ligne": getattr(lo, "montant_ligne", None),
        "devise_ligne": getattr(lo, "devise_ligne", None),
    }


def _invoice_line_from_payload(lo) -> InvoiceLine:
    row = _line_payload_dict(lo)
    return InvoiceLine(
        line_order=row.get("line_order"),
        reference=row.get("reference"),
        designation=row.get("designation"),
        quantite=row.get("quantite"),
        prix_unitaire=row.get("prix_unitaire"),
        montant_ligne=row.get("montant_ligne"),
        devise_ligne=row.get("devise_ligne"),
    )


def _to_line_out(line: InvoiceLine) -> InvoiceLineOut:
    return InvoiceLineOut(
        id=line.id,
        line_order=line.line_order,
        reference=line.reference,
        designation=line.designation,
        quantite=line.quantite,
        prix_unitaire=line.prix_unitaire,
        montant_ligne=line.montant_ligne,
        devise_ligne=line.devise_ligne,
    )


def _to_invoice_out(inv: Invoice, storage: dict | None = None) -> InvoiceOut:
    anomalies_raw = _loads_json(inv.controle_anomalies_json, [])
    anomalies = [DumAnomalyOut(**a) for a in anomalies_raw if isinstance(a, dict)]
    storage_out = StorageOut(**storage) if storage else None
    return InvoiceOut(
        id=inv.id,
        fichier_nom=inv.fichier_nom,
        content_type=inv.content_type,
        statut=inv.statut,
        dossier=inv.dossier,
        uploaded_by_user_id=inv.uploaded_by_user_id,
        dum_document_id=inv.dum_document_id,
        compared_at=inv.compared_at,
        storage=storage_out,
        numero_facture=inv.numero_facture,
        date_facture=inv.date_facture,
        devise=inv.devise,
        client_code=inv.client_code,
        client_nom=inv.client_nom,
        client_pays=inv.client_pays,
        client_matricule_fiscal=inv.client_matricule_fiscal,
        adresse_facturation=inv.adresse_facturation,
        adresse_expedition=inv.adresse_expedition,
        adresse_livraison=inv.adresse_livraison,
        montant_brut=inv.montant_brut,
        montant_remise=inv.montant_remise,
        montant_ht_ou_amount=inv.montant_ht_ou_amount,
        montant_ttc=inv.montant_ttc,
        net_pay=inv.net_pay,
        nombre_colis=inv.nombre_colis,
        poids_brut_kg=inv.poids_brut_kg,
        poids_net_kg=inv.poids_net_kg,
        incoterm=inv.incoterm,
        mode_transport_libelle=inv.mode_transport_libelle,
        conditions_paiement=inv.conditions_paiement,
        notes_reference=inv.notes_reference,
        lines=[_to_line_out(l) for l in inv.lines],
        texte_brut_extrait=inv.texte_brut_extrait,
        extraction_warnings=_loads_json(inv.extraction_warnings_json, []),
        field_confidence=_loads_json(inv.field_confidence_json, {}),
        numero_declaration_dum=inv.numero_declaration_dum,
        montant_declare_dum=inv.montant_declare_dum,
        devise_declaree_dum=inv.devise_declaree_dum,
        ecart_montant=inv.ecart_montant,
        ecart_commentaire=inv.ecart_commentaire,
        statut_controle=inv.statut_controle,
        controle_anomalies=anomalies,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
    )


def _apply_extract_to_invoice(inv: Invoice, data: InvoiceExtractResult) -> None:
    inv.numero_facture = data.numero_facture
    inv.date_facture = data.date_facture
    inv.devise = data.devise
    inv.client_code = data.client_code
    inv.client_nom = data.client_nom
    inv.client_pays = data.client_pays
    inv.client_matricule_fiscal = data.client_matricule_fiscal
    inv.adresse_facturation = data.adresse_facturation
    inv.adresse_expedition = data.adresse_expedition
    inv.adresse_livraison = data.adresse_livraison
    inv.montant_brut = data.montant_brut
    inv.montant_remise = data.montant_remise
    inv.montant_ht_ou_amount = data.montant_ht_ou_amount
    inv.montant_ttc = data.montant_ttc
    inv.net_pay = data.net_pay
    inv.nombre_colis = data.nombre_colis
    inv.poids_brut_kg = data.poids_brut_kg
    inv.poids_net_kg = data.poids_net_kg
    inv.incoterm = data.incoterm
    inv.mode_transport_libelle = data.mode_transport_libelle
    inv.conditions_paiement = data.conditions_paiement
    inv.notes_reference = data.notes_reference
    inv.texte_brut_extrait = data.texte_brut_extrait
    inv.extraction_warnings_json = _dumps_json(data.extraction_warnings)
    inv.field_confidence_json = _dumps_json(data.field_confidence)


def _upload_to_ged(
    *,
    file_bytes: bytes,
    filename: str,
    content_type: str | None,
    uploader_username: str,
) -> tuple[dict | None, dict]:
    nextcloud_meta = None
    nextcloud_error: str | None = None
    fallback_reason = None

    try:
        nextcloud_meta = upload_file_to_nextcloud(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            uploader_name=uploader_username,
        )
    except NextcloudUploadError as exc:
        nextcloud_error = f"Echec du stockage Nextcloud GED: {exc}"
        logger.warning(nextcloud_error)
        from app.config import settings

        if settings.NEXTCLOUD_REQUIRED:
            raise HTTPException(502, nextcloud_error) from exc
    except Exception as exc:
        nextcloud_error = f"Erreur inattendue GED: {exc}"
        logger.warning(nextcloud_error)
        from app.config import settings

        if settings.NEXTCLOUD_REQUIRED:
            raise HTTPException(502, nextcloud_error) from exc

    if not nextcloud_meta:
        from app.config import settings

        if not settings.NEXTCLOUD_ENABLED:
            fallback_reason = "nextcloud-disabled"
        elif nextcloud_error:
            fallback_reason = "nextcloud-upload-error"

    storage_payload = {
        "provider": "nextcloud" if nextcloud_meta else "sql-server-only",
        "nextcloud_path": nextcloud_meta.get("remote_path") if nextcloud_meta else None,
        "nextcloud_url": nextcloud_meta.get("webdav_url") if nextcloud_meta else None,
        "nextcloud_etag": nextcloud_meta.get("etag") if nextcloud_meta else None,
        "fallback_reason": fallback_reason,
        "error": nextcloud_error,
    }
    return nextcloud_meta, storage_payload


@router.post("/extract", response_model=InvoiceExtractResult)
async def extract_only(
    file: UploadFile = File(...),
    _current_user: AuthUser = Depends(get_current_user),
):
    if file.content_type not in _ALLOWED and not (file.filename or "").lower().endswith(
        (".pdf", ".png", ".jpg", ".jpeg")
    ):
        raise HTTPException(400, "Format accepté: PDF, PNG, JPG")
    raw = await file.read()
    return extract_invoice_from_bytes(
        raw,
        filename=file.filename or "document",
        content_type=file.content_type,
    )


@router.post("", response_model=InvoiceOut)
async def create_invoice_from_upload(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    client_pc_name: str | None = Header(default=None, alias="X-Client-PC-Name"),
):
    """Upload + GED Nextcloud + trace + extraction + persistance (OCR_Extraction_DB)."""
    if file.content_type not in _ALLOWED and not (file.filename or "").lower().endswith(
        (".pdf", ".png", ".jpg", ".jpeg")
    ):
        raise HTTPException(400, "Format accepté: PDF, PNG, JPG")

    raw = await file.read()
    original_filename = file.filename or "document"
    user_id = current_user.id
    username = current_user.username

    logger.info("invoice_upload_start file=%s bytes=%s", original_filename, len(raw))
    extracted = extract_invoice_from_bytes(
        raw,
        filename=original_filename,
        content_type=file.content_type,
    )
    logger.info("invoice_extract_done file=%s warnings=%s", original_filename, len(extracted.extraction_warnings or []))

    nextcloud_meta, storage_payload = _upload_to_ged(
        file_bytes=raw,
        filename=original_filename,
        content_type=file.content_type,
        uploader_username=username,
    )

    inv = Invoice(
        fichier_nom=original_filename,
        content_type=file.content_type,
        statut="extracted",
        dossier=nextcloud_meta.get("remote_path") if nextcloud_meta else None,
        uploaded_by_user_id=user_id,
    )
    _apply_extract_to_invoice(inv, extracted)
    for lo in extracted.lines:
        inv.lines.append(
            InvoiceLine(
                line_order=lo.line_order,
                reference=lo.reference,
                designation=lo.designation,
                quantite=lo.quantite,
                prix_unitaire=lo.prix_unitaire,
                montant_ligne=lo.montant_ligne,
                devise_ligne=lo.devise_ligne,
            )
        )
    db.add(inv)
    db.flush()

    local_dossier = None
    try:
        local_dossier = save_local_invoice_file(inv.id, raw, original_filename)
    except OSError as exc:
        logger.warning("invoice_local_storage_failed id=%s err=%s", inv.id, exc)
    if local_dossier:
        inv.dossier = local_dossier
        db.flush()
        logger.info("invoice_local_storage_ok id=%s path=%s", inv.id, local_dossier)
    elif nextcloud_meta:
        inv.dossier = nextcloud_meta.get("remote_path")

    trace = InvoiceUploadTrace(
        invoice_id=inv.id,
        uploaded_by_user_id=user_id,
        uploaded_by_username=username,
        source_filename=original_filename,
        source_content_type=file.content_type,
        source_size_bytes=len(raw),
        client_pc_name=(client_pc_name or "").strip()[:255] or None,
        client_ip=request.client.host if request.client else None,
        client_user_agent=(request.headers.get("user-agent") or "")[:512] or None,
        nextcloud_path=nextcloud_meta.get("remote_path") if nextcloud_meta else None,
        nextcloud_url=nextcloud_meta.get("webdav_url") if nextcloud_meta else None,
        nextcloud_etag=nextcloud_meta.get("etag") if nextcloud_meta else None,
    )
    db.add(trace)
    db.commit()
    db.refresh(inv)
    return _to_invoice_out(inv, storage_payload)


def _resolve_invoice_owners(db: Session, rows: list[Invoice]) -> dict[int, str]:
    """Propriétaire affichable (historique admin) : trace upload puis table users."""
    if not rows:
        return {}

    invoice_ids = [inv.id for inv in rows]
    owners: dict[int, str] = {}

    traces = (
        db.query(InvoiceUploadTrace)
        .filter(InvoiceUploadTrace.invoice_id.in_(invoice_ids))
        .order_by(InvoiceUploadTrace.uploaded_at.desc(), InvoiceUploadTrace.id.desc())
        .all()
    )
    for trace in traces:
        if trace.invoice_id in owners:
            continue
        name = (trace.uploaded_by_username or "").strip()
        if name:
            owners[trace.invoice_id] = name

    user_ids = {
        inv.uploaded_by_user_id
        for inv in rows
        if inv.id not in owners and inv.uploaded_by_user_id is not None
    }
    if user_ids:
        users = db.query(UserRef).filter(UserRef.id.in_(user_ids)).all()
        user_labels = {
            u.id: (u.username or u.email or "").strip() or f"Utilisateur #{u.id}"
            for u in users
        }
        for inv in rows:
            if inv.id in owners:
                continue
            uid = inv.uploaded_by_user_id
            if uid is not None and uid in user_labels:
                owners[inv.id] = user_labels[uid]

    return owners


def _resolve_dum_meta_for_invoices(db: Session, rows: list[Invoice]) -> dict[int, dict[str, str | None]]:
    """Numéro + date DUM depuis la table documents (anciennes factures sans date_declaration_dum)."""
    dum_ids = {inv.dum_document_id for inv in rows if inv.dum_document_id is not None}
    if not dum_ids:
        return {}
    docs = db.query(DumDocument).filter(DumDocument.id.in_(dum_ids)).all()
    out: dict[int, dict[str, str | None]] = {}
    for doc in docs:
        out[doc.id] = {
            "numero": (doc.numero_declaration or "").strip() or None,
            "date": (doc.date_declaration or "").strip() or None,
        }
    return out


def _invoice_list_items(db: Session, rows: list[Invoice]) -> list[InvoiceListItem]:
    owners = _resolve_invoice_owners(db, rows)
    dum_meta = _resolve_dum_meta_for_invoices(db, rows)
    items: list[InvoiceListItem] = []
    for inv in rows:
        meta = dum_meta.get(inv.dum_document_id) if inv.dum_document_id else None
        numero_dum = inv.numero_declaration_dum or (meta.get("numero") if meta else None)
        date_dum = inv.date_declaration_dum or (meta.get("date") if meta else None)
        items.append(
            InvoiceListItem(
                id=inv.id,
                fichier_nom=inv.fichier_nom,
                numero_facture=inv.numero_facture,
                date_facture=inv.date_facture,
                net_pay=inv.net_pay,
                devise=inv.devise,
                statut=inv.statut,
                dum_document_id=inv.dum_document_id,
                numero_declaration_dum=numero_dum,
                date_declaration_dum=date_dum,
                statut_controle=inv.statut_controle,
                compared_at=inv.compared_at,
                created_at=inv.created_at,
                owner=owners.get(inv.id),
            )
        )
    return items


@router.get("", response_model=InvoiceListPage)
def list_invoices(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Liste paginée des factures (filtrée par auteur si rôle ≠ admin)."""
    page_limit = max(1, min(limit, 200))
    page_skip = max(0, skip)

    query = db.query(Invoice)
    if current_user.role != "admin":
        query = query.filter(
            or_(
                Invoice.uploaded_by_user_id == current_user.id,
                Invoice.uploaded_by_user_id.is_(None),
            )
        )

    total = query.count()
    rows = (
        query.order_by(Invoice.created_at.desc(), Invoice.id.desc())
        .offset(page_skip)
        .limit(page_limit)
        .all()
    )
    return InvoiceListPage(
        items=_invoice_list_items(db, rows),
        total=total,
        skip=page_skip,
        limit=page_limit,
    )


def _remove_invoice(db: Session, inv: Invoice) -> None:
    delete_local_invoice_file(inv.id, inv.dossier)
    db.delete(inv)


@router.post("/bulk-delete")
def bulk_delete_invoices(
    body: BulkDeleteIds,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    deleted: list[int] = []
    failed: list[dict] = []
    seen: set[int] = set()
    for raw_id in body.ids[:200]:
        try:
            invoice_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if invoice_id in seen or invoice_id <= 0:
            continue
        seen.add(invoice_id)
        inv = db.get(Invoice, invoice_id)
        if not inv:
            failed.append({"id": invoice_id, "detail": "not_found"})
            continue
        try:
            assert_invoice_access(inv, current_user)
        except HTTPException:
            failed.append({"id": invoice_id, "detail": "forbidden"})
            continue
        _remove_invoice(db, inv)
        deleted.append(invoice_id)
    if deleted:
        db.commit()
    return {"deleted": deleted, "failed": failed}


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Facture introuvable")
    assert_invoice_access(inv, current_user)
    _remove_invoice(db, inv)
    db.commit()
    return None


@router.get("/by-dum/{dum_document_id}", response_model=Optional[InvoiceListItem])
def get_invoice_by_dum(
    dum_document_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Facture liée à une DUM (liaison 1–1), pour la page détail DUM."""
    inv = find_invoice_linked_to_dum(db, dum_document_id)
    if not inv:
        return None
    assert_invoice_access(inv, current_user)
    return _invoice_list_items(db, [inv])[0]


def _resolve_invoice_storage_path(inv: Invoice, db: Session) -> str | None:
    if inv.dossier:
        return inv.dossier
    trace = (
        db.query(InvoiceUploadTrace)
        .filter(InvoiceUploadTrace.invoice_id == inv.id)
        .order_by(InvoiceUploadTrace.uploaded_at.desc())
        .first()
    )
    if trace and trace.nextcloud_path:
        return trace.nextcloud_path
    return None


@router.get("/{invoice_id}/file")
def get_invoice_source_file(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Retourne le fichier source (Nextcloud) pour l'aperçu dans le frontend."""
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Facture introuvable")
    assert_invoice_access(inv, current_user)
    storage_path = _resolve_invoice_storage_path(inv, db)
    file_bytes = None
    content_type = None
    try:
        if storage_path and is_local_dossier(storage_path):
            file_bytes, content_type = read_local_invoice_file(storage_path)
        elif storage_path:
            try:
                file_bytes, content_type = download_file_from_nextcloud(storage_path)
            except (FileNotFoundError, NextcloudUploadError) as ged_exc:
                logger.warning(
                    "invoice_ged_read_failed id=%s path=%s err=%s",
                    invoice_id,
                    storage_path,
                    ged_exc,
                )
                found = find_local_invoice_by_id(invoice_id)
                if found:
                    file_bytes, content_type = found
                else:
                    raise
        else:
            found = find_local_invoice_by_id(invoice_id)
            if not found:
                raise HTTPException(
                    404,
                    (
                        "Fichier source non disponible pour cette facture. "
                        "Réimportez la facture depuis Import (type Facture) pour régénérer l'aperçu."
                    ),
                )
            file_bytes, content_type = found
    except FileNotFoundError as exc:
        found = find_local_invoice_by_id(invoice_id)
        if found:
            file_bytes, content_type = found
        else:
            raise HTTPException(404, str(exc)) from exc
    except NextcloudUploadError as exc:
        found = find_local_invoice_by_id(invoice_id)
        if found:
            file_bytes, content_type = found
        else:
            raise HTTPException(502, str(exc)) from exc
    media_type = content_type or inv.content_type or "application/octet-stream"
    filename = inv.fichier_nom or f"facture_{invoice_id}.pdf"
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Facture introuvable")
    assert_invoice_access(inv, current_user)
    return _to_invoice_out(inv)


@router.patch("/{invoice_id}", response_model=InvoiceOut)
def patch_invoice(
    invoice_id: int,
    body: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Facture introuvable")
    assert_invoice_access(inv, current_user)
    data = body.model_dump(exclude_unset=True)
    lines = data.pop("lines", None)
    for key, val in data.items():
        if hasattr(inv, key):
            setattr(inv, key, val)
    if lines is not None:
        inv.lines.clear()
        for lo in lines:
            inv.lines.append(_invoice_line_from_payload(lo))
    db.commit()
    db.refresh(inv)
    return _to_invoice_out(inv)


@router.post("/{invoice_id}/link-dum", response_model=InvoiceOut)
def link_invoice_to_dum(
    invoice_id: int,
    body: LinkDumBody,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Liaison 1–1 : une facture ↔ un document DUM (documents.id)."""
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Facture introuvable")
    assert_invoice_access(inv, current_user)

    release_dum_from_other_invoices(db, body.dum_document_id, invoice_id)

    try:
        doc = assert_dum_available(db, body.dum_document_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

    inv.dum_document_id = body.dum_document_id
    inv.numero_declaration_dum = (doc.numero_declaration or "").strip() or None
    inv.date_declaration_dum = (doc.date_declaration or "").strip() or None
    db.commit()
    db.refresh(inv)
    return _to_invoice_out(inv)


@router.post("/{invoice_id}/compare-dum", response_model=InvoiceOut)
def compare_with_dum(
    invoice_id: int,
    body: CompareDumBody,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """Compare NET PAY facture au PFN DUM (body ou DUM liee en base)."""
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Facture introuvable")
    assert_invoice_access(inv, current_user)

    merged = merge_compare_body(db, inv, body)
    if merged.dum_document_id and inv.dum_document_id != merged.dum_document_id:
        release_dum_from_other_invoices(db, merged.dum_document_id, invoice_id)
        try:
            doc = assert_dum_available(db, merged.dum_document_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        inv.dum_document_id = merged.dum_document_id
        inv.numero_declaration_dum = (doc.numero_declaration or "").strip() or None
        inv.date_declaration_dum = (doc.date_declaration or "").strip() or None

    pfn = merged.montant_pfn_dum if merged.montant_pfn_dum is not None else merged.montant_declare_dum
    if pfn is None and inv.dum_document_id:
        doc = assert_dum_available(db, inv.dum_document_id)
        merged = document_to_compare_body(doc)

    pfn = merged.montant_pfn_dum if merged.montant_pfn_dum is not None else merged.montant_declare_dum
    if pfn is None:
        raise HTTPException(
            422,
            "montant_pfn_dum requis (body, ou liez une DUM via POST /link-dum ou dum_document_id).",
        )

    result = compare_invoice_with_dum(inv, merged)

    inv.montant_declare_dum = float(pfn)
    inv.devise_declaree_dum = merged.devise_dum or merged.devise_declaree_dum
    inv.numero_declaration_dum = merged.numero_declaration_dum or inv.numero_declaration_dum
    if inv.dum_document_id and not inv.date_declaration_dum:
        try:
            doc_sync = assert_dum_available(db, inv.dum_document_id)
            inv.date_declaration_dum = (doc_sync.date_declaration or "").strip() or None
        except ValueError:
            pass
    inv.ecart_montant = result.ecart_montant
    inv.ecart_commentaire = result.ecart_commentaire
    inv.statut_controle = result.statut_controle
    inv.controle_anomalies_json = _dumps_json([a.model_dump() for a in result.anomalies])
    inv.compared_at = datetime.utcnow()
    if result.statut_controle == "ok":
        inv.statut = "controle_ok"
    elif result.statut_controle == "warning":
        inv.statut = "controle_warning"
    else:
        inv.statut = "controle_ecart"

    db.commit()
    db.refresh(inv)
    return _to_invoice_out(inv)
