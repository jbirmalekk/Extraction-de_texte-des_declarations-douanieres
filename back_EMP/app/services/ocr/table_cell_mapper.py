"""Strict table-cell mapper for customs declaration fields."""

from __future__ import annotations

import re


def _to_float_or_none(value):
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9,.\-]", "", str(value)).replace(",", ".")
    try:
        return float(cleaned) if cleaned else None
    except Exception:
        return None


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _group_rows(cells, y_tolerance=14):
    rows = []
    sorted_cells = sorted(cells, key=lambda c: (c.get("box", (0, 0, 0, 0))[1], c.get("box", (0, 0, 0, 0))[0]))
    for cell in sorted_cells:
        text = _normalize_text(cell.get("text", ""))
        if not text:
            continue
        x, y, w, h = cell.get("box", (0, 0, 0, 0))
        if not rows or abs(y - rows[-1]["y"]) > y_tolerance:
            rows.append({"y": y, "cells": [{"x": x, "text": text, "w": w, "h": h}]})
        else:
            rows[-1]["cells"].append({"x": x, "text": text, "w": w, "h": h})
    for row in rows:
        row["cells"].sort(key=lambda c: c["x"])
        row["line"] = " ".join(c["text"] for c in row["cells"])
    return rows


def map_fields_from_cells(cells: list[dict]) -> dict:
    """Extract fields from table cells by strict row/cell patterns."""
    if not cells:
        return {}

    rows = _group_rows(cells)
    out = {}

    for row in rows:
        line = row["line"].upper()

        # Logistics row
        m_log = re.search(
            r"(?:FRONTIERE|FRONTI[ÈE]RE)[^\d]{0,20}(\d{1,3}).{0,60}DESTINATION[^\d]{0,20}(\d{1,4}).{0,60}(EXPORT|IMPORT|TRANSIT)",
            line,
            re.IGNORECASE,
        )
        if m_log:
            out["bureau_frontiere"] = m_log.group(1)
            out["destination"] = m_log.group(2)
            out["localisation_export"] = m_log.group(3).upper()

        # QCS/PFN row
        m_qcs = re.search(
            r"CODE\s+QCS[^\d]{0,12}(\d{1,3}).{0,25}\bQCS\b[^\d]{0,12}(\d{1,5}).{0,25}\bPFN\b[^\d]{0,12}(\d{1,12}(?:[.,]\d{1,3})?)",
            line,
            re.IGNORECASE,
        )
        if m_qcs:
            out["code_qcs"] = m_qcs.group(1)
            out["qcs"] = m_qcs.group(2)
            out["pfn"] = m_qcs.group(3).replace(",", ".")

        # Weight row
        m_w = re.search(
            r"POIDS\s+BRUT(?:\(KG\))?[^\d]{0,15}(\d{1,5}).{0,40}POIDS\s+NET(?:\(KG\))?[^\d]{0,15}(\d{1,5})",
            line,
            re.IGNORECASE,
        )
        if m_w:
            brut = int(m_w.group(1))
            net = int(m_w.group(2))
            if brut > 0 and net > 0 and brut >= net:
                out["poids_brut"] = str(brut)
                out["poids_net"] = str(net)

        # Regime codes row
        m_reg = re.search(
            r"(?:REGLEMENT|REGIME)\s+FINANCIER[^\d]{0,12}(\d{1,2}).{0,25}(?:C\s*DELAI|CODE\s+DELAI|DELAI)[^\d]{0,12}(\d{1,2}).{0,25}(?:CODE\s+OCI|OCI)[^\d]{0,12}(\d{1,2})",
            line,
            re.IGNORECASE,
        )
        if m_reg:
            out["code_regime_financier"] = m_reg.group(1)
            out["code_delai"] = m_reg.group(2)
            out["code_oci"] = m_reg.group(3)

        # Liquidation metadata row
        m_escale = re.search(r"N[°O]?\s*D[\'’]?\s*ESCALE[^\d]{0,12}(\d{3,6})", line, re.IGNORECASE)
        if m_escale:
            out["numero_escale"] = m_escale.group(1)
        m_rub = re.search(r"\bRUBRIQUE\b[^\d]{0,12}(\d{1,6})", line, re.IGNORECASE)
        if m_rub:
            out["rubrique"] = m_rub.group(1)
        m_rep = re.search(r"N[°O]?\s*REPERTOIRE[^\d]{0,12}(\d{3,6})", line, re.IGNORECASE)
        if m_rep:
            out["num_repertoire"] = m_rep.group(1)

    # Final strict sanity
    if out.get("destination") and str(out["destination"]).isdigit() and int(out["destination"]) < 10:
        out.pop("destination", None)
    for key in ("code_regime_financier", "code_delai", "code_oci"):
        if out.get(key) and (not str(out[key]).isdigit() or not (1 <= int(out[key]) <= 99)):
            out.pop(key, None)
    if out.get("poids_brut") and out.get("poids_net"):
        b = _to_float_or_none(out["poids_brut"])
        n = _to_float_or_none(out["poids_net"])
        if b is None or n is None or b < n:
            out.pop("poids_brut", None)
            out.pop("poids_net", None)

    return out
