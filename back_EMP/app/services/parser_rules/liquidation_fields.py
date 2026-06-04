"""GDT, bureau, movement, itinerary, auth keys."""

from __future__ import annotations

import re

from .customs_helpers import (
    _normalize_route,
    _set_amount_field,
    _set_field,
)


def extract_liquidation_fields(data, source):
    gdt_match = re.search(r"(?:Code\s+GDT|GDT)[\s\S]{0,120}?\b(602)\s+(\d{1,12}[,.]\d{3})", source, re.IGNORECASE)
    if not gdt_match:
        gdt_match = re.search(r"\b(602)\s+(\d{1,12}[,.]\d{3})\b", source)
    if gdt_match:
        _set_field(data, "code_gdt", gdt_match.group(1), force=True)
        _set_amount_field(data, "montant_liquidation", gdt_match.group(2), force=True)

    bureau_match = re.search(r"\b(\d{1,3})\s+BR\s*-\s*(ARIANA|TUNIS|SFAX|BIZERTE)\b", source, re.IGNORECASE)
    if bureau_match:
        bureau = f"BR - {bureau_match.group(2).upper()}"
        _set_field(data, "code_bureau", bureau_match.group(1), force=True)
        _set_field(data, "bureau_douane", bureau, force=True)
        _set_field(data, "designation_bureau", bureau, force=True)

    movement_match = re.search(r"\b(\d{1,3})\s+(\d{1,4})\s+(EXPORT|IMPORT|TRANSIT)\s+\d{1,2}[,.]\d{6,8}", source, re.IGNORECASE)
    if movement_match:
        _set_field(data, "bureau_frontiere", movement_match.group(1), force=True)
        _set_field(data, "destination", movement_match.group(2), force=True)
        _set_field(data, "localisation_export", movement_match.group(3).upper(), force=True)

    colis_match = re.search(r"\b99999\s+(\d{1,4})\b", source)
    if colis_match:
        _set_field(data, "nombre_colis", colis_match.group(1), force=True)

    itinerary_candidates = re.findall(r"\b([A-Z]{2,12})\s*-\s*([A-Z]{2,12})\b", source.upper())
    for left, right in itinerary_candidates:
        candidate = _normalize_route(f"{left}-{right}")
        if candidate:
            _set_field(data, "itineraire", candidate, force=True)
            break

    agrement_match = re.search(r"\b(935)\s*[|:/\-]?\s*(\d{3,5})\b", source)
    if agrement_match:
        _set_field(data, "num_agrement", agrement_match.group(1), force=True)
        _set_field(data, "num_repertoire", agrement_match.group(2), force=True)

    auth_match = re.search(
        r"\b(D\d{2,6}[A-Z]{2,4}\d[A-Z])\b\s*[,/|]?\s*(\d{6,12})?",
        source,
        re.IGNORECASE,
    )
    if auth_match:
        _set_field(data, "cle_authentification", auth_match.group(1).upper(), force=True)
        if auth_match.group(2):
            _set_field(data, "qr_code", auth_match.group(2), force=True)

    if data.get("date_declaration"):
        _set_field(data, "date_validation", data.get("date_declaration"), force=True)

    amount = data.get("montant_liquidation")
    if amount:
        _set_amount_field(data, "montant_total", amount, force=True)
        _set_amount_field(data, "total", amount, force=True)
        _set_amount_field(data, "totaux", amount, force=True)
