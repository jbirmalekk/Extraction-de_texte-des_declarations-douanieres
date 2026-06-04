"""Sauvegarde des crops OCR pour calibration (partie 3 — debug zones)."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import cv2

from app.config import settings

logger = logging.getLogger("app.ocr.zone_debug")


def _debug_root() -> Path | None:
    raw = (getattr(settings, "OCR_DEBUG_SAVE_DIR", "") or "").strip()
    if not raw:
        return None
    root = Path(raw)
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_zone_crop(img, field_name: str, box: tuple[int, int, int, int], *, tag: str = "zone") -> str | None:
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
    session = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = root / session
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in field_name)
    path = out_dir / f"{tag}_{safe_name}.png"
    try:
        cv2.imwrite(str(path), crop)
        logger.info("[OCR DEBUG] saved_crop path=%s", path)
        return str(path)
    except Exception as exc:
        logger.warning("[OCR DEBUG] save_crop_failed field=%s err=%s", field_name, exc)
        return None
