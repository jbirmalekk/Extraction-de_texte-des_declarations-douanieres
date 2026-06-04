"""Template crop field extraction."""

from __future__ import annotations

import re

from .customs_constants import SHORT_NUMERIC_FIELD_BOUNDS
from .customs_helpers import (
    _clean_exporter_name,
    _country_label_from_text,
    _fold_text,
    _has_value,
    _normalize_date_value,
    _normalize_route,
    _set_amount_field,
    _set_field,
    _looks_like_bad_importer,
    _numeric_cell_token,
    _clean_scalar,
)


def extract_template_text_fields(data, zones_text):
    """Read direct field crops emitted by template_extractor.py."""
    if not zones_text:
        return

    for key, value in zones_text.items():
        if not str(key).startswith("tpl_") or not value:
            continue

        field = str(key)[4:]
        if field.startswith("block_"):
            continue
        text_value = _clean_scalar(value)
        folded = _fold_text(text_value)

        if field in {"exportateur", "exportateur_nom"}:
            exporter = _clean_exporter_name(text_value)
            if exporter:
                _set_field(data, "exportateur_nom", exporter, force=True)
                _set_field(data, "exportateur", exporter, force=True)
            continue

        if field == "adresse_exportateur":
            if text_value:
                _set_field(data, field, text_value, force=not _has_value(data.get(field)))
            continue

        if field in {"importateur", "importateur_nom"}:
            if text_value and not _looks_like_bad_importer(text_value):
                _set_field(data, "importateur_nom", text_value, force=True)
                _set_field(data, "importateur", text_value, force=True)
            continue

        if field in {"declarant", "declarant_nom", "nom_declarant"}:
            if text_value and len(re.sub(r"[^A-Za-z]", "", text_value)) >= 3:
                declarant = re.sub(r"\s+", " ", text_value).strip()
                _set_field(data, "declarant_nom", declarant, force=True)
                _set_field(data, "declarant", declarant, force=True)
                _set_field(data, "nom_declarant", declarant, force=True)
            continue

        if field in {
            "pays_provenance", "pays_achat", "pays_premiere_destination",
            "pays_destination", "pays_destination_finale",
        }:
            country = _country_label_from_text(text_value)
            if country:
                _set_field(data, field, country, force=True)
                if field == "pays_destination_finale":
                    _set_field(data, "pays_destination", country, force=True)
            continue

        if field in {"numero_declaration", "date_declaration", "type_declaration"}:
            if field == "numero_declaration":
                match = re.search(r"\b(\d{6})\b", text_value or "")
                if match:
                    _set_field(data, field, match.group(1), force=True)
            elif field == "date_declaration":
                match = re.search(r"\b(\d{2}[\/\-.]\d{2}[\/\-.]\d{4})\b", text_value or "")
                date_value = _normalize_date_value(match.group(1)) if match else None
                _set_field(data, field, date_value, force=True)
            elif field == "type_declaration":
                match = re.search(r"\b(EA|SE|EE|DUM|IM\d*|EX\d*|T1)\b", folded)
                if match:
                    _set_field(data, field, match.group(1), force=True)
            continue

        if field in SHORT_NUMERIC_FIELD_BOUNDS:
            min_value, max_value = SHORT_NUMERIC_FIELD_BOUNDS[field]
            token = _numeric_cell_token(
                text_value,
                min_value=min_value,
                max_value=max_value,
                reject_cases=True,
                prefer_last=True,
            )
            if token:
                _set_field(data, field, token, force=True)
            continue

        if field in {"code_gdt", "code_bureau"}:
            token = _numeric_cell_token(
                text_value,
                min_value=1,
                max_value=999,
                reject_cases=False,
                prefer_last=False,
            )
            if token:
                _set_field(data, field, token, force=True)
            continue

        if field in {
            "bureau_frontiere", "destination", "poids_brut", "poids_net",
            "qualite_fiscale", "code_regime_financier", "code_delai",
        }:
            token = _numeric_cell_token(
                text_value,
                min_value=1,
                max_value=99999,
                reject_cases=field not in {"bureau_frontiere", "destination", "code_regime_financier", "code_delai"},
                prefer_last=True,
            )
            if token:
                _set_field(data, field, token, force=True)
            continue

        if field in {"montant_ptfn", "valeur_fob_dt", "valeur_dinars", "taux_conversion", "montant_liquidation"}:
            match = re.search(r"\b(\d{1,12}[,\.]\d{3,8})\b", text_value or "")
            if match:
                _set_amount_field(data, field, match.group(1), force=True)
            continue

        if field == "bureau_douane":
            match = re.search(r"\bBR\s*-\s*(ARIANA|TUNIS|SFAX|BIZERTE)\b", text_value or "", re.IGNORECASE)
            if match:
                _set_field(data, field, f"BR - {match.group(1).upper()}", force=True)
            continue

        if field == "itineraire":
            match = re.search(r"\b([A-Z]{2,12})\s*-\s*([A-Z]{2,12})\b", text_value or "", re.IGNORECASE)
            if match:
                route = _normalize_route(f"{match.group(1).upper()}-{match.group(2).upper()}")
                if route:
                    _set_field(data, field, route, force=True)
            continue

        _set_field(data, field, text_value, force=field in {
            "bureau_douane", "adresse_entreposage", "mode_transport",
            "transport_international_identite", "itineraire",
        })
