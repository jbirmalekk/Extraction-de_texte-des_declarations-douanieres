"""Transport modes, Incoterms, payment / buyer-seller relation."""

from __future__ import annotations

import re

from .customs_helpers import (
    _is_small_condition_code,
    _normalize_date_value,
    _set_field,
)


def extract_transport_fields(data, source):
    normalized_source = source.replace("â„¢", "T").replace("Ã¢â€žÂ¢", "T")

    normalized_source = source
    for noise in ("\u2122", "\u00e2\u201e\u00a2", "\u00c3\u00a2\u00e2\u20ac\u017e\u00c2\u00a2"):
        normalized_source = normalized_source.replace(noise, "T")

    maritime_match = re.search(r"\b(NAVIRE|BATEAU|VESSEL)\b", normalized_source, re.IGNORECASE)
    if maritime_match:
        identity = "BATEAU" if maritime_match.group(1).upper() == "BATEAU" else "NAVIRE"
        _set_field(data, "mode_transport", identity, force=True)
        _set_field(data, "transport_international_identite", identity, force=True)
        _set_field(data, "transport_international_mode", "7 - MARITIME", force=True)

    if re.search(r"\bVOL\s+DU\b", source, re.IGNORECASE):
        _set_field(data, "mode_transport", "VOL DU", force=True)
        _set_field(data, "transport_international_identite", "VOL DU", force=True)
        _set_field(data, "transport_international_mode", "2 - AERIEN", force=True)

    for match in re.finditer(
        r"\b(?:NAVIRE|BATEAU|VESSEL|VOL\s+DU)\b[\s\S]{0,260}?(\d{2}[\/\-.]\d{2}[\/\-.]\d{4})",
        normalized_source,
        re.IGNORECASE,
    ):
        date_value = _normalize_date_value(match.group(1))
        if date_value:
            _set_field(data, "date_arrivee_depart", date_value, force=True)
            break

    national_match = re.search(r"\bT?N\s+4\s+CAMION\b", source.replace("™", "T"), re.IGNORECASE)
    if re.search(r"\bT?N\s+7\s+(?:NAVIRE|BATEAU|VESSEL)\b", normalized_source, re.IGNORECASE):
        _set_field(data, "transport_international_mode", "7 - MARITIME", force=True)

    if national_match:
        _set_field(data, "transport_national_mode", "4 - ROUTIER", force=True)

    mode_match = re.search(
        r"\b(EXW|CFR|DAP|FOB|CIF|CIP|CPT|DDP|FCA|FAS|DAT)\b[^\n\d]{0,12}"
        r"(\d{1,2})(?![\/\-.])(?:[^\n\d]{1,12}(\d{1,2})(?![\/\-.]))?",
        source,
        re.IGNORECASE,
    )
    if mode_match:
        _set_field(data, "mode_livraison", mode_match.group(1).upper(), force=True)
        if mode_match.group(2) and _is_small_condition_code(mode_match.group(2)):
            _set_field(data, "mode_paiement", mode_match.group(2), force=True)
        if mode_match.group(3) and _is_small_condition_code(mode_match.group(3)):
            _set_field(data, "relation_acheteur_vendeur", mode_match.group(3), force=True)

    labeled_condition_match = re.search(
        r"\b(EXW|CFR|DAP|FOB|CIF|CIP|CPT|DDP|FCA|FAS|DAT)\b"
        r"[\s\S]{0,120}?(?:Mode\s+paiement|paiement)[^\d]{0,40}([1-9])\b"
        r"[\s\S]{0,120}?(?:Rel(?:ation)?|Ach\.?\s*/?\s*vend)[^\d]{0,40}([1-9])\b",
        source,
        re.IGNORECASE,
    )
    if labeled_condition_match:
        _set_field(data, "mode_livraison", labeled_condition_match.group(1).upper(), force=True)
        _set_field(data, "mode_paiement", labeled_condition_match.group(2), force=True)
        _set_field(data, "relation_acheteur_vendeur", labeled_condition_match.group(3), force=True)
