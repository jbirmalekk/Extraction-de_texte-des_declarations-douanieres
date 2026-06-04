"""Common normalization layer shared by OCR engines."""

from __future__ import annotations

import re

COUNTRY_MAP = {
    "TN": "TUNISIE",
    "US": "USA",
    "FR": "FRANCE",
    "DE": "ALLEMAGNE",
    "IT": "ITALIE",
    "ES": "ESPAGNE",
    "BE": "BELGIQUE",
    "CY": "CHYPRE",
    "CN": "CHINE",
    "TR": "TURQUIE",
    "NL": "PAYS BAS",
    "GB": "ROYAUME UNI",
    "PT": "PORTUGAL",
}


def normalize_ocr_text(value: str, *, field_name: str | None = None, profile: str | None = None) -> str:
    if not value:
        return ""
    text = str(value)
    text = text.replace("\r", "\n")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -|:;,.")
    text = text.replace("™", "T")
    text = text.replace("U S A", "USA").replace("U.S.A", "USA")
    text = re.sub(r"\b1N\b", "TN", text)
    text = re.sub(r"\bTM\b", "TN", text)

    fname = (field_name or "").lower()
    profile = (profile or "").lower()

    # Normalize dates to dd-mm-yyyy.
    if "date" in fname:
        match = re.search(r"\b(\d{2})[\/\-.](\d{2})[\/\-.](\d{4})\b", text)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    # Keep only numeric-like characters for strict numeric fields.
    if profile == "numeric" or any(k in fname for k in ("code", "numero", "num_", "colis", "poids", "montant", "qcs", "delai", "regime")):
        numeric = re.sub(r"[^0-9,.\-]", "", text)
        numeric = re.sub(r"\s+", "", numeric)
        numeric = re.sub(r"\.{2,}", ".", numeric)
        return numeric or text

    # Country normalization as CODE LABEL when identifiable.
    if fname.startswith("pays_") or fname in {"pays_destination", "importateur_pays"}:
        up = text.upper()
        for code, label in COUNTRY_MAP.items():
            if re.search(rf"\b{code}\b", up) or re.search(rf"\b{label}\b", up):
                return f"{code} {label}"

    # Controlled uppercase for identity and logistics fields.
    if any(k in fname for k in ("importateur", "exportateur", "declarant", "bureau", "itineraire", "mode_transport", "designation")):
        return text.upper()

    return text
