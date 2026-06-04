"""Declaration header fields (numéro, date, type, colis)."""

from __future__ import annotations

import re

from .customs_helpers import (
    _fold_text,
    _has_value,
    _normalize_date_value,
    _numeric_cell_token,
    _set_field,
)


def extract_header_fields(data, source):
    header = source[:3000]

    for match in re.finditer(r"\b(\d{6})\s+(\d{2}[\/\-.]\d{2}[\/\-.]\d{4})\b", header):
        date_value = _normalize_date_value(match.group(2))
        if date_value:
            _set_field(data, "numero_declaration", match.group(1), force=True)
            _set_field(data, "date_declaration", date_value, force=True)
            break

    if not _has_value(data.get("numero_declaration")):
        number_match = re.search(
            r"(?:DECLARATION|NUMERO|N[°O]?)\D{0,90}\b(\d{6})\b",
            _fold_text(header),
        )
        if number_match:
            _set_field(data, "numero_declaration", number_match.group(1), force=True)

    folded_header = _fold_text(header)

    if not _has_value(data.get("date_declaration")):
        date_match = re.search(
            r"(?:DATE|DECLARATION)\D{0,120}\b(\d{2}[\/\-.]\d{2}[\/\-.]\d{4})\b",
            header,
            re.IGNORECASE,
        )
        if date_match:
            date_value = _normalize_date_value(date_match.group(1))
            if date_value:
                _set_field(data, "date_declaration", date_value, force=True)

    type_match = re.search(
        r"TYPE\s+(?:DECLARATION|ESCIATATION)[\s\S]{0,160}?\b(EA|SE|EE|DUM|IM\s*\d{0,3}|EX\s*\d{0,3}|T1)\b",
        folded_header,
    )
    if not type_match:
        type_match = re.search(r"\b(EA|SE|DUM|IM\s*\d{0,3}|EX\s*\d{0,3}|T1)\b\s+\d{1,3}\s+\d{1,4}\b", folded_header)
    if type_match:
        declaration_type = re.sub(r"\s+", "", type_match.group(1))
        _set_field(data, "type_declaration", declaration_type, force=True)

    counts_match = re.search(
        r"\b(?:EA|SE|EE|DUM|IM\s*\d{0,3}|EX\s*\d{0,3}|T1)\b"
        r"[^\d]{0,18}(\d{1,2})[^\d]{1,18}(\d{1,4})\b",
        folded_header,
    )
    if counts_match:
        article_count = _numeric_cell_token(
            counts_match.group(1),
            min_value=1,
            max_value=99,
            reject_cases=True,
            prefer_last=False,
        )
        colis_count = _numeric_cell_token(
            counts_match.group(2),
            min_value=1,
            max_value=999,
            reject_cases=True,
            prefer_last=False,
        )
        if article_count:
            _set_field(data, "nbre_articles", article_count, force=True)
            _set_field(data, "nombre_articles", article_count, force=True)
        if colis_count:
            _set_field(data, "nombre_colis", colis_count, force=True)

    if not _has_value(data.get("nombre_colis")):
        colis_match = re.search(r"\b99999\s+(\d{1,4})\b", source)
        if not colis_match:
            colis_match = re.search(r"\b(?:Nbre|Nombre|bre)\s*colis[^\d]{0,40}(\d{1,4})\b", source, re.IGNORECASE)
        if colis_match:
            _set_field(data, "nombre_colis", colis_match.group(1), force=True)

    export_code_match = re.search(r"\b(\d{6,8}[A-Z])\b", header, re.IGNORECASE)
    if export_code_match:
        _set_field(data, "exportateur_code", export_code_match.group(1).upper(), force=True)
        _set_field(data, "code_exportateur", export_code_match.group(1).upper(), force=True)
