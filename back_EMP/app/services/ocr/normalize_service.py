"""Normalization stage for parsed OCR payload."""

import re
from datetime import datetime


def _fix_typo_year_in_date(value):
    """OCR often reads 2026 as 3026 (digit confusion)."""
    if not value:
        return value
    s = str(value).strip().replace("/", "-").replace(".", "-")
    m = re.fullmatch(r"(\d{2})-(\d{2})-(\d{4})", s)
    if not m:
        return value
    dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
    y = int(yyyy)
    if 3000 <= y <= 3099:
        y2 = y - 1000
        candidate = f"{dd}-{mm}-{y2}"
        try:
            datetime.strptime(candidate, "%d-%m-%Y")
            return candidate
        except Exception:
            pass
    return s


def apply_post_parse_normalization(parsed: dict) -> dict:
    if str(parsed.get("bureau_frontiere") or "").strip() == "7" and str(parsed.get("destination") or "").strip() == "4":
        parsed["bureau_frontiere"] = None
        parsed["destination"] = None

    if str(parsed.get("code_regime_financier") or "").strip() in {"45", "46", "47", "48", "49", "50", "56"}:
        parsed["code_regime_financier"] = None
    if str(parsed.get("code_delai") or "").strip() in {"45", "46", "47", "48", "49", "50", "56"}:
        parsed["code_delai"] = None

    if str(parsed.get("itineraire") or "").strip().upper() == "FAX-RADES":
        parsed["itineraire"] = "SFAX-RADES"

    for key in ("date_declaration", "date_validation", "date_arrivee_depart"):
        if parsed.get(key):
            parsed[key] = _fix_typo_year_in_date(parsed[key])

    return parsed
