"""Validation et correction importateur/exportateur via référentiel métier."""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

from app.config import settings

logger = logging.getLogger("app.ocr.party_referential")

_PARTY_KEYS = (
    "exportateur_nom",
    "exportateur",
    "importateur_nom",
    "importateur",
    "code_importateur",
    "exportateur_code",
    "adresse_exportateur",
    "adresse_importateur",
)


def _default_referential_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "importateur_referential.json"


def normalize_importateur_code(raw: str | None) -> str | None:
    """Normalise CL 101, cl101, 5751 → clé référentiel."""
    if not raw:
        return None
    text = re.sub(r"\s+", "", str(raw).upper().strip())
    m = re.search(r"CL(\d{1,4})", text)
    if m:
        return f"CL{m.group(1)}"
    m = re.search(r"\b(\d{3,5})\b", text)
    if m:
        return m.group(1)
    return text or None


def _fold_name(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").upper()).strip()


def _name_similarity(a: str, b: str) -> float:
    """Score simple 0–1 basé sur tokens communs (≥4 car.)."""
    ta = {t for t in _fold_name(a).split() if len(t) >= 4}
    tb = {t for t in _fold_name(b).split() if len(t) >= 4}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


@lru_cache(maxsize=1)
def load_importateur_referential() -> dict[str, str]:
    path_raw = (getattr(settings, "OCR_IMPORTATEUR_REFERENTIAL_PATH", "") or "").strip()
    path = Path(path_raw) if path_raw else _default_referential_path()
    if not path.is_file():
        logger.warning("Référentiel importateur introuvable: %s", path)
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Référentiel importateur illisible: %s (%s)", path, exc)
        return {}
    out: dict[str, str] = {}
    for key, value in payload.items():
        if str(key).startswith("_") or not value:
            continue
        norm = normalize_importateur_code(str(key)) or str(key).upper()
        out[norm] = _fold_name(str(value))
        if norm.startswith("CL") and norm[2:].isdigit():
            out[norm[2:]] = out[norm]
    return out


def lookup_importateur_name(code: str | None) -> str | None:
    ref = load_importateur_referential()
    norm = normalize_importateur_code(code)
    if not norm:
        return None
    if norm in ref:
        return ref[norm]
    if norm.startswith("CL") and norm[2:] in ref:
        return ref[norm[2:]]
    return None


def apply_party_referential_validation(data: dict) -> dict:
    """
    Validation CONSULTATIVE (aucun forçage) : ne modifie jamais les valeurs OCR.
    Si le code importateur est connu et que le nom OCR diffère fortement,
    ajoute uniquement un flag pour attirer l'attention du validateur humain.
    """
    if not data or not isinstance(data, dict):
        return data

    code = data.get("code_importateur")
    ref_name = lookup_importateur_name(code)
    if not ref_name:
        return data

    flags = set(data.get("flags_validation") or [])
    current = _fold_name(str(data.get("importateur_nom") or data.get("importateur") or ""))

    if not current:
        # Ne remplit rien : signale seulement qu'une référence existe pour ce code.
        flags.add("importateur_referential_hint_available")
    else:
        sim = _name_similarity(current, ref_name)
        if sim < 0.35:
            flags.add("importateur_referential_mismatch")
        elif sim < 0.65:
            flags.add("importateur_referential_partial_match")

    data["flags_validation"] = sorted(flags)
    return data
