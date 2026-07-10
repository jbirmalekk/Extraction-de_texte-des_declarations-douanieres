"""Sauvegarde des crops OCR pour calibration (partie 3 — debug zones)."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2

from app.config import settings

logger = logging.getLogger("app.ocr.zone_debug")

_session_id: str | None = None
_session_dir: Path | None = None
_zone_records: list[dict[str, Any]] = []


def _debug_root() -> Path | None:
    raw = (getattr(settings, "OCR_DEBUG_SAVE_DIR", "") or "").strip()
    if not raw:
        return None
    root = Path(raw)
    if not root.is_absolute():
        root = Path.cwd() / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def begin_debug_session(*, filename: str = "") -> Path | None:
    """Démarre une session debug unique pour tout le traitement d'un document."""
    global _session_id, _session_dir, _zone_records
    if not settings.OCR_DEBUG_ZONES:
        return None
    root = _debug_root()
    if root is None:
        return None
    _session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    _session_dir = root / _session_id
    _session_dir.mkdir(parents=True, exist_ok=True)
    _zone_records = []
    meta = {"started_at": _session_id, "source_filename": filename}
    try:
        (_session_dir / "session_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("[OCR DEBUG] session_meta_failed err=%s", exc)
    logger.info("[OCR DEBUG] session_start dir=%s", _session_dir)
    return _session_dir


def get_debug_session_dir() -> Path | None:
    return _session_dir


def record_zone_ocr(
    field_name: str,
    *,
    tag: str = "zone",
    ocr_text: str | None = None,
    confidence: float | None = None,
    engine: str | None = None,
    crop_path: str | None = None,
    box: tuple[int, int, int, int] | None = None,
) -> None:
    if not settings.OCR_DEBUG_ZONES or _session_dir is None:
        return
    _zone_records.append(
        {
            "field": field_name,
            "tag": tag,
            "ocr_text": (ocr_text or "").strip(),
            "confidence": confidence,
            "engine": engine,
            "crop_path": crop_path,
            "box": list(box) if box else None,
        }
    )


def save_zone_crop(
    img,
    field_name: str,
    box: tuple[int, int, int, int],
    *,
    tag: str = "zone",
    ocr_text: str | None = None,
    confidence: float | None = None,
    engine: str | None = None,
) -> str | None:
    """Enregistre un crop PNG si OCR_DEBUG_ZONES et OCR_DEBUG_SAVE_DIR sont actifs."""
    if not settings.OCR_DEBUG_ZONES:
        return None
    root = _debug_root()
    if root is None or img is None:
        return None
    x1, y1, x2, y2 = box
    h, w = img.shape[:2]
    x1, x2 = max(0, min(w, x1)), max(0, min(w, x2))
    y1, y2 = max(0, min(h, y1)), max(0, min(h, y2))
    if x2 <= x1 or y2 <= y1:
        return None
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    if _session_dir is None:
        begin_debug_session()
    out_dir = _session_dir or (root / datetime.now().strftime("%Y%m%d_%H%M%S"))
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in field_name)
    path = out_dir / f"{tag}_{safe_name}.png"
    try:
        cv2.imwrite(str(path), crop)
        record_zone_ocr(
            field_name,
            tag=tag,
            ocr_text=ocr_text,
            confidence=confidence,
            engine=engine,
            crop_path=str(path),
            box=box,
        )
        logger.info("[OCR DEBUG] saved_crop path=%s", path)
        return str(path)
    except Exception as exc:
        logger.warning("[OCR DEBUG] save_crop_failed field=%s err=%s", field_name, exc)
        return None


def finalize_debug_session(final_fields: dict[str, Any] | None = None) -> str | None:
    """Écrit le manifeste JSON (crops + valeurs OCR + résultat final)."""
    global _session_id, _session_dir, _zone_records
    if not settings.OCR_DEBUG_ZONES or _session_dir is None:
        return None

    party_fields = {}
    if final_fields:
        for key in (
            "exportateur_nom",
            "exportateur",
            "exportateur_code",
            "adresse_exportateur",
            "importateur_nom",
            "importateur",
            "code_importateur",
            "adresse_importateur",
            "declarant_nom",
            "declarant_code",
            "num_repertoire",
        ):
            if final_fields.get(key):
                party_fields[key] = final_fields.get(key)

    manifest = {
        "session_id": _session_id,
        "zone_records": _zone_records,
        "final_party_fields": party_fields,
        "field_reject_reasons": final_fields.get("field_reject_reasons") if final_fields else [],
        "flags_validation": final_fields.get("flags_validation") if final_fields else [],
    }
    manifest_path = _session_dir / "extraction_manifest.json"
    try:
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("[OCR DEBUG] manifest_saved path=%s zones=%s", manifest_path, len(_zone_records))
    except OSError as exc:
        logger.warning("[OCR DEBUG] manifest_failed err=%s", exc)
        manifest_path = None

    _session_id = None
    _session_dir = None
    _zone_records = []
    return str(manifest_path) if manifest_path else None
