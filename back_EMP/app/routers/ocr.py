from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import String
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from typing import Any
import logging
import subprocess

from pytesseract import TesseractNotFoundError

# Importer TON get_db existant
from app.database import get_db
from app.config import settings

from app.models.document import (
    Document,
    Taxe,
    Article,
    DocumentUploadTrace,
    OCRResult,
    ExtractedField,
    ValidationSession,
    CorrectionHistory,
)
from app.models.user import User
from app.models.schemas import (
    OCRResultSchema,
    OCRValidationSchema,
    DocumentResponseSchema,
    BulkDeleteIdsSchema,
)
from app.routers.auth import get_current_user
from app.services.storage.document_file_storage import (
    delete_local_document_file,
    document_has_stored_file,
    find_local_document_by_id,
    is_local_dossier,
    local_dossier_for_document_id,
    read_local_document_file,
    save_local_document_file,
)
from app.services.storage.nextcloud_storage import (
    NextcloudUploadError,
    download_file_from_nextcloud,
    upload_file_to_nextcloud,
)
from app.services.pipeline import process_document
from app.services.quality.document_quality import assess_upload_document

router = APIRouter(prefix="/api", tags=["OCR"])


def _assert_user_can_access_document(
    doc: Document,
    user: User,
    db: Session | None = None,
) -> None:
    """Même règle d'accès pour détail, corrections et fichier source (admin = tout)."""
    if user.role == "admin":
        return

    owner_id = doc.uploaded_by_user_id
    if owner_id is not None:
        try:
            if int(owner_id) != int(user.id):
                raise HTTPException(status_code=403, detail="Acces non autorise")
        except (TypeError, ValueError):
            if owner_id != user.id:
                raise HTTPException(status_code=403, detail="Acces non autorise")
        return

    if db is None:
        return

    trace = (
        db.query(DocumentUploadTrace)
        .filter(DocumentUploadTrace.document_id == doc.id)
        .order_by(DocumentUploadTrace.uploaded_at.desc())
        .first()
    )
    trace_owner = trace.uploaded_by_user_id if trace else None
    if trace_owner is None:
        return
    try:
        if int(trace_owner) != int(user.id):
            raise HTTPException(status_code=403, detail="Acces non autorise")
    except (TypeError, ValueError):
        if trace_owner != user.id:
            raise HTTPException(status_code=403, detail="Acces non autorise")


logger = logging.getLogger(__name__)


EXTRACTED_FIELD_KEYS = [
    "exportateur", "adresse_exportateur", "code_exportateur",
    "importateur", "adresse_importateur", "code_importateur",
    "declarant", "repertoire", "numero_credit",
    "numero_declaration", "date_declaration", "type_declaration", "nbre_articles",
    "numero_dae", "nombre_articles", "nombre_colis",
    "exportateur_nom", "exportateur_code",
    "importateur_nom", "importateur_pays",
    "declarant_code", "declarant_nom",
    "transport_international_nationalite", "transport_international_mode",
    "transport_international_identite", "transport_national_nationalite",
    "transport_national_mode",
    "mode_transport", "date_arrivee_depart", "pays_provenance", "pays_destination",
    "pays_achat", "pays_premiere_destination", "pays_destination_finale",
    "adresse_entreposage", "mode_livraison", "devise", "montant_ptfn",
    "mode_paiement", "relation_acheteur_vendeur", "engagement", "valeur_totale",
    "assurance", "fret", "valeur_dinars", "engag_c", "solde_autres_elements_ptfn", "cours_conversion_zone",
    "valeur_fob_dt", "taux_conversion", "designation_marchandises", "poids_brut",
    "poids_net", "numero_article", "code_sh_ndp", "code_pays_origine",
    "valeur_prise_en_charge", "code_qcs", "qcs", "pfn", "qualite_fiscale",
    "regime_douanier", "imposition_speciale", "code_titre_ce", "numero_titre_ce",
    "code_regime_precedent", "code_regime_financier", "code_regime_transit",
    "code_delai", "code_oci", "regime", "valeur_fob", "douane", "coefficient_ajustement",
    "description_marchandise",
    "bureau_frontiere", "destination", "localisation_export",
    "bureau_douane", "code_bureau", "designation_bureau",
    "code_taxe", "assiette", "quotite", "montant",
    "code_gdt", "montant_liquidation", "montant_total", "total", "totaux", "itineraire", "certificat_decharge", "numero_escale", "rubrique",
    "commissaire_douane", "texte_engagement", "nom_declarant", "date_validation", "cachet",
    "num_agrement", "num_repertoire", "cle_authentification", "score_confiance", "qualite",
    "qr_code",
]

VALIDATABLE_DOCUMENT_FIELDS = [
    "numero_declaration", "date_declaration", "type_declaration",
    "nbre_articles", "exportateur_nom", "exportateur_code", "importateur_nom",
    "importateur_pays", "declarant_code", "declarant_nom", "mode_transport",
    "date_arrivee_depart", "pays_provenance", "pays_destination", "adresse_entreposage",
    "mode_livraison", "devise", "montant_ptfn", "valeur_fob_dt", "taux_conversion",
    "designation_marchandises", "poids_brut", "poids_net", "bureau_douane", "code_gdt",
    "montant_liquidation", "itineraire", "num_agrement", "num_repertoire",
    "cle_authentification",
]

RESERVED_VALIDATION_KEYS = {"document_id", "statut"}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_field_value(value: Any) -> str | None:
    serialized = _normalize_text(value)
    return serialized if serialized else None


def _normalize_validation_status(status: str | None) -> str:
    candidate = _normalize_text(status).lower()
    mapping = {
        "validated": "validated",
        "valide": "validated",
        "rejected": "rejected",
        "rejete": "rejected",
        "in_progress": "in_progress",
        "inprogress": "in_progress",
        "processing": "in_progress",
    }
    return mapping.get(candidate, "in_progress")


def _session_to_document_status(session_status: str) -> str:
    if session_status == "validated":
        return "validated"
    if session_status == "rejected":
        return "rejected"
    return "processing"


def _hydrate_document_from_result(doc: Document, result: dict[str, Any]) -> None:
    """Copy matching scalar OCR keys to Document columns when available."""
    if not result:
        return

    ignored = {"taxes", "articles", "flags_validation", "storage", "erreur"}
    for key, value in result.items():
        if key in ignored:
            continue
        if hasattr(doc, key):
            setattr(doc, key, value)


def _clamp_document_strings(doc: Document) -> None:
    """Truncate string columns to SQL Server limits (avoids 500 + misleading CORS errors)."""
    for column in Document.__table__.columns:
        col_type = getattr(column, "type", None)
        max_len = getattr(col_type, "length", None)
        if not isinstance(col_type, String) or not max_len:
            continue
        raw = getattr(doc, column.name, None)
        if raw is None or not isinstance(raw, str):
            continue
        if len(raw) > max_len:
            setattr(doc, column.name, raw[:max_len])


@router.post("/ocr")
async def extract_declaration(
    request: Request,
    file: UploadFile = File(...),
    fast_mode: bool = False,
    use_deskew: bool = True,
    client_pc_name: str | None = Header(default=None, alias="X-Client-PC-Name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    allowed = {"image/jpeg","image/png","image/tiff",
               "application/pdf","image/jpg"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400,
                            detail="Format non supporte (JPG, PNG, TIFF, PDF)")

    file_bytes = await file.read()
    original_filename = file.filename or "document"

    # Analyse qualité (CPU) déléguée au threadpool : ne bloque pas l'event loop.
    document_quality = await run_in_threadpool(
        assess_upload_document, file_bytes, file.content_type
    )
    if document_quality.get("block"):
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Qualite du document insuffisante pour l'OCR",
                "document_quality": document_quality,
            },
        )

    nextcloud_meta = None
    nextcloud_error: str | None = None

    try:
        # Upload GED = I/O réseau bloquant (requests) → threadpool.
        nextcloud_meta = await run_in_threadpool(
            upload_file_to_nextcloud,
            file_bytes=file_bytes,
            filename=original_filename,
            content_type=file.content_type,
            uploader_name=current_user.username,
        )
    except NextcloudUploadError as exc:
        nextcloud_error = f"Echec du stockage Nextcloud GED: {exc}"
        logger.warning(nextcloud_error)
        if settings.NEXTCLOUD_REQUIRED:
            raise HTTPException(
                status_code=502,
                detail=nextcloud_error,
            )
    except Exception as exc:
        nextcloud_error = f"Erreur inattendue lors du stockage Nextcloud GED: {exc}"
        logger.warning(nextcloud_error)
        if settings.NEXTCLOUD_REQUIRED:
            raise HTTPException(
                status_code=502,
                detail=nextcloud_error,
            )

    fallback_reason = None
    if not nextcloud_meta:
        if not settings.NEXTCLOUD_ENABLED:
            fallback_reason = "nextcloud-disabled"
            logger.info("Nextcloud GED desactive; stockage SQL uniquement.")
        elif nextcloud_error:
            fallback_reason = "nextcloud-upload-error"

    try:
        # OCR = tâche CPU longue (plusieurs secondes) → threadpool obligatoire,
        # sinon tout le serveur est bloqué pendant l'extraction.
        result = await run_in_threadpool(
            process_document,
            file_bytes=file_bytes,
            filename=original_filename,
            fast_mode=fast_mode,
            use_deskew=use_deskew,
        )
    except (TesseractNotFoundError, subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.exception("ocr_tesseract_unavailable fichier=%s", original_filename)
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Le moteur OCR Tesseract n'est pas disponible ou ne demarre pas.",
                "hint": (
                    "Reinstallez Tesseract OCR (Windows), ajoutez-le au PATH, "
                    "puis verifiez TESSERACT_PATH dans back_EMP/.env "
                    f"(actuel: {settings.TESSERACT_PATH or 'non defini'})."
                ),
                "error": str(exc)[:500],
            },
        ) from exc
    except Exception as exc:
        logger.exception("ocr_process_failed fichier=%s", original_filename)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Erreur interne lors de l'extraction OCR.",
                "error": str(exc)[:500],
            },
        ) from exc

    if "erreur" in result:
        detail = (
            f"{result['erreur']} | fichier={file.filename} | type={file.content_type}"
        )
        raise HTTPException(status_code=422, detail=detail)

    storage_payload = {
        "provider": "nextcloud" if nextcloud_meta else "sql-server-only",
        "nextcloud_path": nextcloud_meta.get("remote_path") if nextcloud_meta else None,
        "nextcloud_url": nextcloud_meta.get("webdav_url") if nextcloud_meta else None,
        "nextcloud_etag": nextcloud_meta.get("etag") if nextcloud_meta else None,
        "fallback_reason": fallback_reason,
        "error": nextcloud_error,
    }
    result["storage"] = storage_payload
    result["document_quality"] = document_quality

    # Sauvegarder en base
    doc = Document(
        fichier                  = result.get("fichier"),
        dossier                  = nextcloud_meta.get("remote_path") if nextcloud_meta else None,
        uploaded_by_user_id      = current_user.id,
        statut                   = "done",
        numero_declaration       = result.get("numero_declaration"),
        date_declaration         = result.get("date_declaration"),
        type_declaration         = result.get("type_declaration"),
        nbre_articles            = result.get("nbre_articles"),
        exportateur_nom          = result.get("exportateur_nom"),
        exportateur_code         = result.get("exportateur_code"),
        importateur_nom          = result.get("importateur_nom"),
        importateur_pays         = result.get("importateur_pays"),
        declarant_code           = result.get("declarant_code"),
        declarant_nom            = result.get("declarant_nom"),
        mode_transport           = result.get("mode_transport"),
        date_arrivee_depart      = result.get("date_arrivee_depart"),
        pays_provenance          = result.get("pays_provenance"),
        pays_destination         = result.get("pays_destination"),
        adresse_entreposage      = result.get("adresse_entreposage"),
        mode_livraison           = result.get("mode_livraison"),
        devise                   = result.get("devise"),
        montant_ptfn             = result.get("montant_ptfn"),
        valeur_fob_dt            = result.get("valeur_fob_dt"),
        taux_conversion          = result.get("taux_conversion"),
        designation_marchandises = result.get("designation_marchandises"),
        poids_brut               = result.get("poids_brut"),
        poids_net                = result.get("poids_net"),
        bureau_douane            = result.get("bureau_douane"),
        code_gdt                 = result.get("code_gdt"),
        montant_liquidation      = result.get("montant_liquidation"),
        itineraire               = result.get("itineraire"),
        num_agrement             = result.get("num_agrement"),
        num_repertoire           = result.get("num_repertoire"),
        cle_authentification     = result.get("cle_authentification"),
        score_confiance          = result.get("score_confiance"),
        qualite                  = result.get("qualite"),
        flags_validation         = result.get("flags_validation", []),
        texte_brut               = result.get("texte_brut","")[:5000],
    )
    _hydrate_document_from_result(doc, result)
    _clamp_document_strings(doc)
    db.add(doc)
    try:
        db.flush()
    except SQLAlchemyError as exc:
        logger.exception("ocr_save_failed fichier=%s", original_filename)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Echec enregistrement en base (donnees trop longues ou invalides).",
                "hint": str(exc.orig) if getattr(exc, "orig", None) else str(exc),
            },
        ) from exc

    local_dossier = None
    try:
        local_dossier = save_local_document_file(doc.id, file_bytes, original_filename)
    except OSError as exc:
        logger.warning("dum_local_storage_failed id=%s err=%s", doc.id, exc)
    if local_dossier:
        doc.dossier = local_dossier
        db.flush()
        logger.info("dum_local_storage_ok id=%s path=%s", doc.id, local_dossier)
    elif nextcloud_meta:
        doc.dossier = nextcloud_meta.get("remote_path")
    else:
        logger.warning(
            "dum_no_storage_path id=%s fichier=%s (aperçu historique indisponible sans réimport)",
            doc.id,
            original_filename,
        )

    ocr_result = OCRResult(
        document_id=doc.id,
        raw_result_json=result,
        global_confidence=_to_float_or_none(result.get("score_confiance")),
        engine_name=str(result.get("ocr_engine_used") or "tesseract"),
    )
    db.add(ocr_result)
    db.flush()

    for field_key in EXTRACTED_FIELD_KEYS:
        field_value = _to_field_value(result.get(field_key))
        if field_value is None:
            continue

        db.add(ExtractedField(
            ocr_result_id=ocr_result.id,
            field_key=field_key,
            value=field_value,
            confidence=None,
            manually_added=False,
        ))

    trace = DocumentUploadTrace(
        document_id=doc.id,
        uploaded_by_user_id=current_user.id,
        uploaded_by_username=current_user.username,
        source_filename=original_filename,
        source_content_type=file.content_type,
        source_size_bytes=len(file_bytes),
        client_pc_name=(client_pc_name or "").strip()[:255] or None,
        client_ip=request.client.host if request.client else None,
        client_user_agent=(request.headers.get("user-agent") or "")[:512] or None,
        nextcloud_path=nextcloud_meta.get("remote_path") if nextcloud_meta else None,
        nextcloud_url=nextcloud_meta.get("webdav_url") if nextcloud_meta else None,
        nextcloud_etag=nextcloud_meta.get("etag") if nextcloud_meta else None,
    )
    db.add(trace)

    for t in result.get("taxes", []):
        db.add(Taxe(
            document_id = doc.id,
            code        = t.get("code"),
            assiette    = t.get("assiette"),
            quotite     = t.get("quotite"),
            montant     = t.get("montant"),
        ))

    for a in result.get("articles", []):
        db.add(Article(
            document_id   = doc.id,
            num_ligne     = a.get("num_ligne"),
            code_hs       = a.get("code_hs"),
            designation   = a.get("designation"),
            quantite      = a.get("quantite"),
            unite         = a.get("unite"),
            prix_unitaire = a.get("prix_unitaire"),
            total_ligne   = a.get("total_ligne"),
        ))

    db.commit()
    db.refresh(doc)

    result["id"] = doc.id
    result["dossier"] = doc.dossier
    result["storage_local"] = bool(local_dossier)
    return JSONResponse(content=result)


@router.put("/ocr/{document_id}/valider")
async def valider_declaration(
    document_id : int,
    data        : OCRValidationSchema,
    current_user: User = Depends(get_current_user),
    db          : Session = Depends(get_db),
):
    if data.document_id != document_id:
        raise HTTPException(status_code=400, detail="document_id payload mismatch")

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouve")

    session_status = _normalize_validation_status(data.statut)
    validation_session = ValidationSession(
        document_id=doc.id,
        validator_user_id=current_user.id,
        status=session_status,
    )
    if session_status in {"validated", "rejected"}:
        validation_session.ended_at = datetime.utcnow()
    db.add(validation_session)
    db.flush()

    ocr_result = doc.ocr_result
    if ocr_result is None:
        ocr_result = OCRResult(
            document_id=doc.id,
            raw_result_json={},
            global_confidence=_to_float_or_none(doc.score_confiance),
            engine_name="legacy-backfill",
        )
        db.add(ocr_result)
        db.flush()

    extracted_fields_by_key = {f.field_key: f for f in ocr_result.extracted_fields}
    raw_result_payload = dict(ocr_result.raw_result_json or {})
    corrections_count = 0
    session_corrections: list[dict[str, Any]] = []

    incoming_payload = data.model_dump(exclude_none=True)
    editable_keys = [
        key for key in incoming_payload.keys()
        if key not in RESERVED_VALIDATION_KEYS
    ]

    for ch in editable_keys:
        incoming = incoming_payload.get(ch)
        if incoming is None:
            continue

        old_value = getattr(doc, ch, None) if hasattr(doc, ch) else raw_result_payload.get(ch)
        old_norm = _normalize_text(old_value)
        new_norm = _normalize_text(incoming)
        if old_norm == new_norm:
            continue

        if hasattr(doc, ch):
            setattr(doc, ch, incoming)
        raw_result_payload[ch] = incoming

        extracted_field = extracted_fields_by_key.get(ch)
        if extracted_field is None:
            extracted_field = ExtractedField(
                ocr_result_id=ocr_result.id,
                field_key=ch,
                value=incoming,
                confidence=None,
                manually_added=True,
            )
            db.add(extracted_field)
            db.flush()
            extracted_fields_by_key[ch] = extracted_field
        else:
            extracted_field.value = incoming

        if old_norm == "" and new_norm != "":
            action_type = "add"
        elif old_norm != "" and new_norm == "":
            action_type = "delete"
        else:
            action_type = "update"

        changed_at = datetime.utcnow()
        history_entry = CorrectionHistory(
            validation_session_id=validation_session.id,
            extracted_field_id=extracted_field.id,
            changed_by_user_id=current_user.id,
            old_value=old_value,
            new_value=incoming,
            action_type=action_type,
            changed_at=changed_at,
        )
        db.add(history_entry)
        session_corrections.append({
            "field_key": ch,
            "old_value": old_value,
            "new_value": incoming,
            "action_type": action_type,
            "modified_by_username": current_user.username,
            "modified_at": changed_at.isoformat(),
        })
        corrections_count += 1

    ocr_result.raw_result_json = raw_result_payload
    doc.statut = _session_to_document_status(session_status)
    db.commit()

    return {
        "message": "Validation enregistree",
        "id": doc.id,
        "statut": doc.statut,
        "validation_session_id": validation_session.id,
        "corrections_count": corrections_count,
        "corrections": session_corrections,
    }


@router.get("/ocr/{document_id}/corrections/latest")
async def get_latest_corrections(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouve")

    rows = (
        db.query(CorrectionHistory, ExtractedField, User)
        .join(
            ValidationSession,
            CorrectionHistory.validation_session_id == ValidationSession.id,
        )
        .outerjoin(
            ExtractedField,
            CorrectionHistory.extracted_field_id == ExtractedField.id,
        )
        .outerjoin(
            User,
            CorrectionHistory.changed_by_user_id == User.id,
        )
        .filter(ValidationSession.document_id == document_id)
        .order_by(CorrectionHistory.changed_at.desc(), CorrectionHistory.id.desc())
        .all()
    )

    latest_by_field: dict[str, dict[str, Any]] = {}
    for history_row, extracted_field, changed_by_user in rows:
        field_key = extracted_field.field_key if extracted_field else None
        if not field_key or field_key in latest_by_field:
            continue

        latest_by_field[field_key] = {
            "field_key": field_key,
            "old_value": history_row.old_value,
            "new_value": history_row.new_value,
            "action_type": history_row.action_type,
            "modified_by_username": (
                changed_by_user.username if changed_by_user else None
            ),
            "modified_at": (
                history_row.changed_at.isoformat() if history_row.changed_at else None
            ),
            "validation_session_id": history_row.validation_session_id,
        }

    return {
        "document_id": document_id,
        "latest_corrections": latest_by_field,
    }


@router.get("/ocr/{document_id}/corrections")
async def list_document_corrections(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Timeline complète des corrections pour l'historique / détail document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouve")
    _assert_user_can_access_document(doc, current_user, db)

    rows = (
        db.query(CorrectionHistory, ExtractedField, User)
        .join(
            ValidationSession,
            CorrectionHistory.validation_session_id == ValidationSession.id,
        )
        .outerjoin(
            ExtractedField,
            CorrectionHistory.extracted_field_id == ExtractedField.id,
        )
        .outerjoin(User, CorrectionHistory.changed_by_user_id == User.id)
        .filter(ValidationSession.document_id == document_id)
        .order_by(CorrectionHistory.changed_at.desc(), CorrectionHistory.id.desc())
        .all()
    )

    items = []
    for history_row, extracted_field, changed_by_user in rows:
        items.append(
            {
                "id": history_row.id,
                "field_key": extracted_field.field_key if extracted_field else None,
                "old_value": history_row.old_value,
                "new_value": history_row.new_value,
                "action_type": history_row.action_type,
                "modified_by_username": changed_by_user.username if changed_by_user else None,
                "modified_at": history_row.changed_at.isoformat() if history_row.changed_at else None,
                "validation_session_id": history_row.validation_session_id,
            }
        )

    return {"document_id": document_id, "corrections": items, "total": len(items)}


@router.get("/documents", response_model=list[DocumentResponseSchema])
async def liste_documents(
    skip  : int = 0,
    limit : int = 50,
    current_user: User = Depends(get_current_user),
    db    : Session = Depends(get_db),
):
    query = db.query(Document).order_by(Document.created_at.desc())
    if current_user.role != "admin":
        query = query.filter(Document.uploaded_by_user_id == current_user.id)
    return query.offset(skip).limit(limit).all()


def _serialize_document_detail(doc: Document, db: Session | None = None) -> dict:
    """Réponse détail DUM : colonnes document + articles + taxes + auteur."""
    uploaded_by = None
    if doc.uploaded_by:
        uploaded_by = {
            "id": doc.uploaded_by.id,
            "username": doc.uploaded_by.username,
            "email": getattr(doc.uploaded_by, "email", None),
        }
    articles = [
        {
            "id": a.id,
            "num_ligne": a.num_ligne,
            "code_hs": a.code_hs,
            "designation": a.designation,
            "quantite": a.quantite,
            "unite": a.unite,
            "prix_unitaire": a.prix_unitaire,
            "total_ligne": a.total_ligne,
        }
        for a in (doc.articles or [])
    ]
    taxes = [
        {
            "id": t.id,
            "code": t.code,
            "assiette": t.assiette,
            "quotite": t.quotite,
            "montant": t.montant,
        }
        for t in (doc.taxes or [])
    ]
    payload = {c.name: getattr(doc, c.name, None) for c in Document.__table__.columns}
    payload["uploaded_by"] = uploaded_by
    payload["articles"] = articles
    payload["taxes"] = taxes
    storage_path = _resolve_document_storage_path(doc, db) if db is not None else doc.dossier
    payload["has_source_file"] = document_has_stored_file(doc.id, storage_path)
    return payload


def _resolve_document_storage_path(doc: Document, db: Session) -> str | None:
    if doc.dossier:
        return doc.dossier
    trace = (
        db.query(DocumentUploadTrace)
        .filter(DocumentUploadTrace.document_id == doc.id)
        .order_by(DocumentUploadTrace.uploaded_at.desc())
        .first()
    )
    if trace and trace.nextcloud_path:
        return trace.nextcloud_path
    return local_dossier_for_document_id(doc.id)


def _maybe_repair_local_dossier(doc: Document, db: Session) -> None:
    """Aligne documents.dossier si le fichier local {id}{ext} existe."""
    if doc.dossier and is_local_dossier(doc.dossier):
        return
    local_path = local_dossier_for_document_id(doc.id)
    if local_path and doc.dossier != local_path:
        doc.dossier = local_path
        db.commit()


@router.get("/documents/{document_id}/file")
async def get_document_source_file(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retourne le fichier source (Nextcloud / stockage local) pour l'aperçu frontend."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouve")
    _assert_user_can_access_document(doc, current_user, db)
    _maybe_repair_local_dossier(doc, db)
    storage_path = _resolve_document_storage_path(doc, db)
    file_bytes = None
    content_type = None
    try:
        if storage_path and is_local_dossier(storage_path):
            file_bytes, content_type = read_local_document_file(storage_path)
        elif storage_path:
            try:
                file_bytes, content_type = download_file_from_nextcloud(storage_path)
            except (FileNotFoundError, NextcloudUploadError) as ged_exc:
                logger.warning(
                    "dum_ged_read_failed id=%s path=%s err=%s",
                    document_id,
                    storage_path,
                    ged_exc,
                )
                found = find_local_document_by_id(document_id)
                if found:
                    file_bytes, content_type = found
                else:
                    raise
        else:
            found = find_local_document_by_id(document_id)
            if not found:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Fichier source non disponible pour ce document. "
                        "Réimportez la DUM depuis Import (type DUM) pour régénérer l'aperçu."
                    ),
                )
            file_bytes, content_type = found
    except FileNotFoundError as exc:
        found = find_local_document_by_id(document_id)
        if found:
            file_bytes, content_type = found
        else:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NextcloudUploadError as exc:
        found = find_local_document_by_id(document_id)
        if found:
            file_bytes, content_type = found
        else:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    media_type = content_type or "application/octet-stream"
    filename = doc.fichier or f"document_{document_id}.pdf"
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/documents/{document_id}")
async def get_document(
    document_id : int,
    current_user: User = Depends(get_current_user),
    db          : Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .options(
            joinedload(Document.uploaded_by),
            joinedload(Document.articles),
            joinedload(Document.taxes),
        )
        .filter(Document.id == document_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouve")

    _assert_user_can_access_document(doc, current_user, db)

    return _serialize_document_detail(doc, db)


def _remove_document(db: Session, doc: Document) -> None:
    delete_local_document_file(doc.id, doc.dossier)
    db.delete(doc)


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouve")
    _assert_user_can_access_document(doc, current_user, db)
    _remove_document(db, doc)
    db.commit()
    return None


@router.post("/documents/bulk-delete")
async def bulk_delete_documents(
    body: BulkDeleteIdsSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Supprime plusieurs DUM (fichier local + enregistrement et données liées en cascade)."""
    deleted: list[int] = []
    failed: list[dict[str, Any]] = []
    seen: set[int] = set()
    for raw_id in body.ids[:200]:
        try:
            doc_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if doc_id in seen or doc_id <= 0:
            continue
        seen.add(doc_id)
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            failed.append({"id": doc_id, "detail": "not_found"})
            continue
        try:
            _assert_user_can_access_document(doc, current_user, db)
        except HTTPException:
            failed.append({"id": doc_id, "detail": "forbidden"})
            continue
        _remove_document(db, doc)
        deleted.append(doc_id)
    if deleted:
        db.commit()
    return {"deleted": deleted, "failed": failed}