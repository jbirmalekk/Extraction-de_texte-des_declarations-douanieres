"""Final normalization and false-positive cleanup on parsed customs data."""

from __future__ import annotations

import re

from .customs_helpers import (
    _clean_exporter_name,
    _fold_text,
    _is_form_case_value,
    _is_small_condition_code,
    _looks_like_bad_importer,
    _normalize_route,
    _valid_weight_pair,
)


def apply_final_customs_cleanup(data, source=""):
    source_folded = _fold_text(source)

    exporter = _clean_exporter_name(data.get("exportateur_nom") or data.get("exportateur"))
    if not exporter:
        exporter = _clean_exporter_name(source_folded)
    if exporter:
        data["exportateur_nom"] = exporter
        data["exportateur"] = exporter

    if _looks_like_bad_importer(data.get("importateur_nom")):
        data["importateur_nom"] = None
        data["importateur"] = None

    finance_match = re.search(
        r"(?:CREG|C\.REG|REGLEMENT\s+FINANCIER)[^\d]{0,80}(\d{2})"
        r"[\s\S]{0,120}?(?:C\.?\s*DELAI|DELAI)[^\d]{0,80}(\d{1,2})\b",
        source_folded,
    )
    if finance_match:
        data["code_regime_financier"] = finance_match.group(1)
        data["code_delai"] = finance_match.group(2)

    for key in ("mode_paiement", "relation_acheteur_vendeur"):
        if data.get(key) and not _is_small_condition_code(data.get(key)):
            data[key] = None

    for key, extra in (("fret", {"23"}), ("assurance", {"24"})):
        value = str(data.get(key) or "").strip()
        if value and "." not in value and "," not in value and _is_form_case_value(value, extra=extra):
            data[key] = None

    brut = str(data.get("poids_brut") or "").strip()
    net = str(data.get("poids_net") or "").strip()
    if brut and _is_form_case_value(brut, extra={"45", "65"}):
        data["poids_brut"] = None
        brut = ""
    if net and _is_form_case_value(net, extra={"45", "65"}):
        data["poids_net"] = None
        net = ""
    if brut and net and not _valid_weight_pair(brut, net):
        data["poids_brut"] = None
        data["poids_net"] = None

    if not data.get("poids_brut") or not data.get("poids_net"):
        weight_match = re.search(
            r"POIDS\s+BRUT[^\d]{0,80}(\d{2,5})[\s\S]{0,140}?POIDS\s+NET[^\d]{0,80}(\d{1,5})",
            source_folded,
        )
        if weight_match and _valid_weight_pair(weight_match.group(1), weight_match.group(2)):
            data["poids_brut"] = weight_match.group(1)
            data["poids_net"] = weight_match.group(2)

    if data.get("itineraire"):
        data["itineraire"] = _normalize_route(data.get("itineraire"))
    if not data.get("itineraire") and re.search(r"\bS?FAX\s*-\s*RADES\b", source_folded):
        data["itineraire"] = "SFAX-RADES"

    commissaire = _fold_text(data.get("commissaire_douane"))
    if commissaire and (
        _normalize_route(commissaire)
        or any(token in commissaire for token in ("SFAX - RADES", "SFAX-RADES", "BR -", "RFP", "C.AGREMENT"))
    ):
        data["commissaire_douane"] = None

    code_oci = str(data.get("code_oci") or "").strip()
    if code_oci and (
        _is_form_case_value(code_oci, extra={"21", "11", "56"})
        or code_oci in {str(data.get("code_regime_financier") or ""), str(data.get("code_delai") or "")}
    ):
        data["code_oci"] = None

    if str(data.get("code_regime_financier") or "").strip() in {"45", "46", "47", "48", "49", "50", "56"}:
        data["code_regime_financier"] = None
    if str(data.get("code_delai") or "").strip() in {"45", "46", "47", "48", "49", "50", "56"}:
        data["code_delai"] = None

    if str(data.get("bureau_frontiere") or "").strip() == "7" and str(data.get("destination") or "").strip() == "4":
        data["bureau_frontiere"] = None
        data["destination"] = None

    engagement = _fold_text(data.get("engagement"))
    if engagement and ("EXW" in engagement or len(re.sub(r"[^A-Z]", "", engagement)) < 6):
        data["engagement"] = None

    if data.get("transport_international_identite") in {"NAVIRE", "BATEAU"}:
        data["transport_international_mode"] = "7 - MARITIME"
