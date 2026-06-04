"""Semantic post-processing for OCR-extracted customs fields."""

from __future__ import annotations

import re
from typing import Any


def apply_semantic_normalization(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)

    # Normalize route frequent OCR confusion.
    route = str(normalized.get("itineraire") or "").strip().upper()
    if route == "FAX-RADES":
        normalized["itineraire"] = "SFAX-RADES"

    # Normalize obvious null-like placeholders.
    for key in ("bureau_frontiere", "destination", "code_regime_financier", "code_delai"):
        value = str(normalized.get(key) or "").strip()
        if value in {"0", "00", "000", "45", "46", "47", "48", "49", "50", "56"}:
            normalized[key] = None

    # Keep consistent naming between alias fields.
    if normalized.get("importateur_nom") and not normalized.get("importateur"):
        normalized["importateur"] = normalized["importateur_nom"]
    if normalized.get("exportateur_nom") and not normalized.get("exportateur"):
        normalized["exportateur"] = normalized["exportateur_nom"]
    if normalized.get("declarant_nom") and not normalized.get("declarant"):
        normalized["declarant"] = normalized["declarant_nom"]

    # Standardize decimal separators for monetary/weight values.
    for key in ("poids_brut", "poids_net", "montant_liquidation", "valeur_fob_dt", "taux_conversion"):
        value = normalized.get(key)
        if value is None:
            continue
        text = str(value).strip().replace(" ", "")
        if re.fullmatch(r"\d+[.,]\d+", text):
            normalized[key] = text.replace(",", ".")

    return normalized
