"""Cases 47–50 : Régime, FOB, Douane, coefficient d'ajustement."""

from __future__ import annotations

import re

from .customs_helpers import _has_value, _set_amount_field, _set_field


def _normalize_amount(value: str | None) -> str | None:
    if not value:
        return None
    text = re.sub(r"(?i)\b(?:FOB|DOUANE|DINARS|VALEUR|EN)\b", " ", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    match = re.search(r"\b(\d{1,12}[.,]\d{3})\b", text)
    if match:
        return match.group(1).replace(",", ".")
    match = re.search(r"\b(\d{4,12})\b", text)
    if match:
        return match.group(1)
    return None


def _extract_regime_from_source(text_u: str) -> str | None:
    """
    Case 47/48 « Régime » (ex. 56) — pas confondre avec régimes douaniers 362/532
    ni qualité fiscale / code QCI.
    """
    if not text_u:
        return None

    for pattern in (
        r"\bR[EÉ]GIME\b(?!\s+DOUAN)(?!\s*S\b)[^\d]{0,18}(\d{2})\b",
        r"\bR[EÉ]GIME\s+\d+\b[^\d]{0,12}(\d{2})\b",
        r"(?:CODE\s+)?QCI\b[\s\S]{0,100}?\bR[EÉ]GIME\b[^\d]{0,18}(\d{2})\b",
    ):
        match = re.search(pattern, text_u, re.IGNORECASE)
        if match:
            value = match.group(1)
            if value not in {"36", "53", "62", "32", "21", "11"}:
                return value

    block = re.search(
        r"POIDS\s+NET[\s\S]{0,280}?\bFOB\b",
        text_u,
        re.IGNORECASE,
    )
    if block:
        chunk = block.group(0)
        match = re.search(r"\bR[EÉ]GIME\b[^\d]{0,18}(\d{2})\b", chunk, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r"\b(5[0-9]|[1-4][0-9])\b", chunk)
        if match:
            return match.group(1)

    return None


def _normalize_regime_zone(value: str | None, text_u: str = "") -> str | None:
    if not value:
        return None
    text = re.sub(r"(?i)\b(?:REGIME|RÉGIME|QCI|OCI|QUALITE|FISCAL)\b", " ", str(value))
    tokens = re.findall(r"\b\d{1,2}\b", text)
    if not tokens:
        return None
    two_digit = [t for t in tokens if len(t) == 2 and 10 <= int(t) <= 99]
    if two_digit:
        return two_digit[-1]
    from_source = _extract_regime_from_source(text_u)
    if from_source:
        return from_source
    single = [t for t in tokens if 1 <= int(t) <= 9]
    if len(single) == 1 and not from_source:
        return None
    return None


def _normalize_coef(value: str | None) -> str | None:
    if not value:
        return None
    text = re.sub(r"(?i)\b(?:COEF|AJUSTEMENT|COEFFICIENT)\b", " ", str(value))
    match = re.search(r"\b(\d{1,3}(?:[.,]\d{1,6})?)\b", text)
    if match:
        return match.group(1).replace(",", ".")
    return None


def extract_article_value_fields(data: dict, source: str) -> None:
    text = str(source or "")
    text_u = text.upper()

    m_pair = re.search(
        r"\bFOB\b[^\d]{0,40}(\d{1,12}[.,]\d{3})\b[\s\S]{0,120}?\bDOUANE\b[^\d]{0,40}(\d{1,12}[.,]\d{3})\b",
        text_u,
        re.IGNORECASE,
    )
    if m_pair:
        fob = m_pair.group(1).replace(",", ".")
        dou = m_pair.group(2).replace(",", ".")
        _set_amount_field(data, "valeur_fob", fob, force=True)
        _set_amount_field(data, "douane", dou, force=True)
        if not _has_value(data.get("valeur_fob_dt")):
            _set_amount_field(data, "valeur_fob_dt", fob, force=True)
        if not _has_value(data.get("valeur_dinars")):
            _set_amount_field(data, "valeur_dinars", dou, force=True)

    if not _has_value(data.get("valeur_fob")):
        m_fob = re.search(
            r"\b(?:FOB|VALEUR\s+EN\s+DINARS)\b[^\d]{0,50}(\d{1,12}[.,]\d{3})\b",
            text_u,
            re.IGNORECASE,
        )
        if m_fob:
            _set_amount_field(data, "valeur_fob", m_fob.group(1).replace(",", "."), force=True)

    if not _has_value(data.get("douane")):
        m_dou = re.search(
            r"\bDOUANE\b[^\d]{0,50}(\d{1,12}[.,]\d{3})\b",
            text_u,
            re.IGNORECASE,
        )
        if m_dou:
            _set_amount_field(data, "douane", m_dou.group(1).replace(",", "."), force=True)

    if _has_value(data.get("valeur_fob")) and not _has_value(data.get("valeur_fob_dt")):
        _set_amount_field(data, "valeur_fob_dt", data["valeur_fob"], force=True)
    if _has_value(data.get("douane")) and not _has_value(data.get("valeur_dinars")):
        _set_amount_field(data, "valeur_dinars", data["douane"], force=True)

    regime_ft = _extract_regime_from_source(text_u)
    if regime_ft:
        _set_field(data, "regime", regime_ft, force=True)
    elif not _has_value(data.get("regime")):
        m_reg = re.search(r"\bR[EÉ]GIME\b(?!\s+DOUAN)[^\d]{0,18}(\d{2})\b", text_u, re.IGNORECASE)
        if m_reg:
            _set_field(data, "regime", m_reg.group(1), force=True)

    if not _has_value(data.get("coefficient_ajustement")):
        m_coef = re.search(
            r"\bCOEF(?:FICIENT)?\.?\s*(?:D['’]?\s*)?AJUSTEMENT\b[^\d]{0,30}(\d{1,3}(?:[.,]\d{1,6})?)\b",
            text_u,
            re.IGNORECASE,
        )
        if m_coef:
            _set_field(data, "coefficient_ajustement", m_coef.group(1).replace(",", "."), force=True)


def apply_zone_article_values(data: dict, raw: dict, *, full_text: str = "") -> None:
    """Remplit FOB / Douane / Régime / Coef depuis les crops OCR (field_schema)."""
    text_u = str(full_text or "").upper()

    fob = _normalize_amount(raw.get("valeur_fob"))
    if fob:
        _set_amount_field(data, "valeur_fob", fob, force=True)
    dou = _normalize_amount(raw.get("douane"))
    if dou:
        _set_amount_field(data, "douane", dou, force=True)

    regime_ft = _extract_regime_from_source(text_u)
    if regime_ft:
        _set_field(data, "regime", regime_ft, force=True)
    else:
        reg = _normalize_regime_zone(raw.get("regime"), text_u)
        if reg:
            _set_field(data, "regime", reg, force=True)

    coef = _normalize_coef(raw.get("coefficient_ajustement"))
    if coef:
        _set_field(data, "coefficient_ajustement", coef, force=True)
