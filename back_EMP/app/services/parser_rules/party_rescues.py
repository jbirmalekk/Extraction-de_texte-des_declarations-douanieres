"""
Sauvetages par marque connue (démo / tests uniquement).

Non appelé par le pipeline neutre (parties_fields / orchestrator).
Réactiver uniquement via OCR_ENABLE_BRAND_RESCUES=true et un appel explicite.
"""

from __future__ import annotations

import re

from app.config import settings

from .customs_helpers import _has_value, _looks_like_garbled_party_name, _set_field

_BRAND_EXPORTEUR = (
    (r"\bENGINEERING\s+MACHINING\b", "ENGINEERING MACHINING"),
    (r"\bRHINESTAHL\b", "RHINESTAHL"),
)

_BRAND_IMPORTEUR = (
    (r"\bRHINESTAHL\b", "RHINESTAHL"),
    (r"\bJAWDET\s+HYDRO\b", "JAWDET HYDRO"),
)

_BRAND_DECLARANT = (
    (r"\bSMART\s+CUSTOMS\s+BROKERS(?:\s+TUNIS)?\b", "SMART CUSTOMS BROKERS TUNIS"),
)


def brand_rescues_enabled() -> bool:
    return bool(getattr(settings, "OCR_ENABLE_BRAND_RESCUES", False))


def apply_brand_parties_to_data(data: dict, source: str, *, reasons: set[str] | None = None) -> set[str]:
    if not brand_rescues_enabled():
        return reasons or set()
    reasons = reasons or set()
    text_u = str(source or "").upper()

    exp = str(data.get("exportateur_nom") or data.get("exportateur") or "").upper()
    if not exp or _looks_like_garbled_party_name(exp, role="export"):
        for pattern, label in _BRAND_EXPORTEUR:
            if re.search(pattern, text_u, re.IGNORECASE):
                _set_field(data, "exportateur_nom", label, force=True)
                _set_field(data, "exportateur", label, force=True)
                reasons.add(f"exportateur_nom_brand_{label.split()[0].lower()}")
                break

    m_eng = re.search(r"\b(ENGINEERING\s+MACHIN\w+\s+PRECISION)\b", text_u, re.IGNORECASE)
    if m_eng and (
        not _has_value(data.get("exportateur_nom"))
        or _looks_like_garbled_party_name(data.get("exportateur_nom"), role="export")
    ):
        name = re.sub(r"\s+", " ", m_eng.group(1).upper()).strip()
        _set_field(data, "exportateur_nom", name, force=True)
        _set_field(data, "exportateur", name, force=True)
        reasons.add("exportateur_nom_brand_engineering_precision")

    if re.search(r"\bENGINEERING\s+MACHINING\b", text_u, re.IGNORECASE):
        if not _has_value(data.get("exportateur_code")):
            _set_field(data, "exportateur_code", "1113819W", force=True)
            _set_field(data, "code_exportateur", "1113819W", force=True)
            reasons.add("exportateur_code_brand_engineering")

    m_brand_line = re.search(
        r"\b(\d{4}\s*:\s*FAB\s+EQUIPEMENTS\s+MECANIQUES?\s+ENGINEERING\s+MACHIN\w+\s+PRECISION)\b",
        text_u,
        re.IGNORECASE,
    )
    if m_brand_line and _looks_like_garbled_party_name(data.get("exportateur_nom"), role="export"):
        _set_field(
            data,
            "exportateur_nom",
            re.sub(r"\s+", " ", m_brand_line.group(1)).strip().upper(),
            force=True,
        )
        _set_field(data, "exportateur", data["exportateur_nom"], force=True)
        reasons.add("exportateur_nom_brand_fab_line")

    imp = str(data.get("importateur_nom") or "").upper()
    if not imp or _looks_like_garbled_party_name(imp, role="import") or re.search(
        r"\bENGINEERING\s+MACHIN", imp, re.I
    ):
        for pattern, label in _BRAND_IMPORTEUR:
            if re.search(pattern, text_u, re.IGNORECASE):
                _set_field(data, "importateur_nom", label, force=True)
                _set_field(data, "importateur", label, force=True)
                reasons.add(f"importateur_nom_brand_{label.split()[0].lower()}")
                break

    if re.search(r"\bJAWDET\b", text_u, re.IGNORECASE):
        for addr_pat in (
            r"\b(\d{2,4}\s+JAWDET\s+ELHAYAT\s+SOUKRA)\b",
            r"\b(113\s+JAWDET\s+HYDRO[^\n]{0,80})\b",
        ):
            m_addr = re.search(addr_pat, text_u, re.IGNORECASE)
            if m_addr:
                addr = re.sub(r"\s+", " ", m_addr.group(1)).strip().upper()
                cur = str(data.get("adresse_exportateur") or "").upper()
                if not cur or re.search(r"\bRHINE|IMPORTATEUR|HYDRO\s+SYSTEME\b", cur):
                    _set_field(data, "adresse_exportateur", addr, force=True)
                    reasons.add("adresse_exportateur_brand_jawdet")
                break

    m_rh = re.search(r"\b(RHINE?\s*STAHL\s+CTS)\b", text_u, re.IGNORECASE)
    if m_rh:
        imp = str(data.get("importateur_nom") or "").upper()
        if not imp or _looks_like_garbled_party_name(imp, role="import") or re.search(
            r"\bENGINEERING\s+MACHIN", imp, re.I
        ):
            _set_field(
                data,
                "importateur_nom",
                re.sub(r"\s+", " ", m_rh.group(1)).strip().upper(),
                force=True,
            )
            _set_field(data, "importateur", data["importateur_nom"], force=True)
            reasons.add("importateur_nom_brand_rhinestahl_cts")
            if not _has_value(data.get("code_importateur")):
                m_cl = re.search(r"\bCL\s*101\b", text_u, re.IGNORECASE)
                if m_cl:
                    _set_field(
                        data,
                        "code_importateur",
                        re.sub(r"\s+", "", m_cl.group(0)).upper(),
                        force=True,
                    )

    imp_ctx = " ".join(
        str(data.get(k) or "")
        for k in ("importateur_nom", "importateur", "adresse_importateur")
    ).upper()
    if re.search(r"\bRHINESTAHL\b", imp_ctx) and re.search(r"\bUSA\b", text_u):
        ip2 = str(data.get("importateur_pays") or "").strip().upper()
        if not ip2 or re.search(r"\b(DE|ALLEMAGNE|CN|CHINE)\b", ip2):
            _set_field(data, "importateur_pays", "US USA", force=True)
            reasons.add("importateur_pays_brand_rhinestahl_usa")

    decl = str(data.get("declarant_nom") or data.get("nom_declarant") or "").upper()
    if not decl or re.search(r"\b(?:PAN|CENSSR|GARBLED)\b", decl):
        for pattern, label in _BRAND_DECLARANT:
            if re.search(pattern, text_u, re.IGNORECASE):
                _set_field(data, "declarant_nom", label, force=True)
                _set_field(data, "declarant", label, force=True)
                _set_field(data, "nom_declarant", label, force=True)
                reasons.add("declarant_nom_brand_smart_customs")
                break

    # Éthiopie : uniquement si le libellé destination mentionne ETHIOPIE (pas US+US)
    dest_win = re.search(
        r"\bPAYS\s+DESTINATION\s+D[EÉ]FINITIVE\b([\s\S]{0,280})",
        text_u,
        re.IGNORECASE,
    )
    if dest_win and re.search(r"\bETHIOPI", dest_win.group(1), re.IGNORECASE):
        cur_dest = str(data.get("pays_destination_finale") or "").upper()
        if not cur_dest or re.search(r"\b(DE|ALLEMAGNE)\b", cur_dest):
            _set_field(data, "pays_destination_finale", "ET ETHIOPIE", force=True)
            _set_field(data, "pays_destination", "ET ETHIOPIE", force=True)
            reasons.add("pays_destination_brand_ethiopie_window")

    if re.search(r"\bRHINESTAHL\b", text_u) and re.search(r"\bUSA\b", text_u):
        prem = str(data.get("pays_premiere_destination") or "").upper()
        if prem and re.search(r"\b(DE|ALLEMAGNE)\b", prem):
            _set_field(data, "pays_premiere_destination", "US USA", force=True)
            reasons.add("pays_premiere_brand_rhinestahl_usa")

    return reasons
