"""OCR par sous-cellules du bandeau « Informations générales » (partie 6)."""

from __future__ import annotations

import logging
import re

from app.config import settings
from app.services.ocr.field_schema import HEADER_CELL_ZONES
from app.services.ocr.recognition_service import recognize_detailed
from app.services.ocr.zone_debug import save_zone_crop
from app.services.parser_rules.customs_helpers import _looks_like_garbled_party_name

logger = logging.getLogger("app.ocr.header_cell_ocr")


def _crop_ratio(img, ratio: tuple[float, float, float, float]):
    h, w = img.shape[:2]
    y1, y2, x1, x2 = ratio
    y1i, y2i = int(h * y1), int(h * y2)
    x1i, x2i = int(w * x1), int(w * x2)
    if y2i <= y1i or x2i <= x1i:
        return None, (0, 0, 0, 0)
    box = (x1i, y1i, x2i, y2i)
    return img[y1i:y2i, x1i:x2i], box


def extract_header_cell_fields(img, *, fast_mode: bool = False, ocr_scale: float = 2.0) -> dict[str, str]:
    """
    Lit chaque micro-zone du bandeau haut (grille DUM TTN) avant fusion template.
    """
    if img is None or not getattr(settings, "OCR_ENABLE_HEADER_CELL_OCR", True):
        return {}

    scale = 1.5 if fast_mode else max(2.0, ocr_scale)
    out: dict[str, str] = {}

    for zone in HEADER_CELL_ZONES:
        roi, box = _crop_ratio(img, zone.ratio)
        if roi is None or roi.size == 0:
            continue

        details = recognize_detailed(
            roi,
            psm=zone.psm,
            ocr_scale=scale,
            field_name=zone.name,
            critical=zone.name
            in {
                "exportateur_nom",
                "adresse_exportateur",
                "importateur_nom",
                "code_importateur",
                "adresse_importateur",
                "declarant_nom",
                "pays_destination_finale",
            },
        )
        text = (details.get("text") or "").strip()

        if settings.OCR_DEBUG_ZONES:
            save_zone_crop(
                img,
                zone.name,
                box,
                tag="header_cell",
                ocr_text=text,
                confidence=float(details.get("confidence") or 0.0),
                engine=str(details.get("engine") or ""),
            )

        if not text:
            continue
        cleaned = _post_clean(zone.name, text)
        if cleaned and zone.name == "exportateur_nom" and _looks_like_garbled_party_name(cleaned, role="export"):
            continue
        if cleaned:
            out[zone.name] = cleaned

    return out


def _post_clean(field_name: str, text: str) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    if field_name == "code_importateur":
        m = re.search(r"\b(CL\s*\d{1,4})\b", t, re.IGNORECASE)
        return re.sub(r"\s+", "", m.group(1)).upper() if m else ""
    if field_name.startswith("pays_"):
        m = re.search(r"\b([A-Z]{2})\b", t.upper())
        if m and re.search(r"[A-Z]{4,}", t.upper()):
            return t.upper()[:80]
        return t.upper()[:80]
    return t.upper() if field_name.endswith("_nom") or "adresse" in field_name else t
