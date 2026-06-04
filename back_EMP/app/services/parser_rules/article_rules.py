"""Article extraction rules."""

from __future__ import annotations

import re


def _safe_float(value):
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9.]", "", str(value).replace(",", ".").replace(" ", ""))
    try:
        return float(cleaned) if cleaned else None
    except Exception:
        return None


def extract_articles_from_text(text: str):
    if not text:
        return []

    rows = []
    seen = set()

    def append_row(num_ligne, code_hs):
        key = (num_ligne, code_hs)
        if key in seen:
            return
        seen.add(key)
        rows.append({
            "num_ligne": num_ligne,
            "code_hs": code_hs,
            "designation": None,
            "quantite": None,
            "unite": None,
            "prix_unitaire": None,
            "total_ligne": None,
        })

    article_patterns = [
        r"Article\s*n[°o]?[\s\S]*?(\d{1,3})\s+(\d{8,12})",
        r"^\s*(\d{1,3})\s+(\d{8,12})\s+[A-Z]{2}\s+\d{1,12}(?:[.,]\d+)?",
    ]
    for pattern in article_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            append_row(int(match.group(1)), match.group(2))

    qty_total_match = re.search(
        r"PEN\s+de\s+l['’]article[\s\S]*?\d{1,3}\s+(\d{1,12}(?:[.,]\d+)?)\s+(\d{1,12}(?:[.,]\d+)?)",
        text,
        re.IGNORECASE,
    )
    if rows and qty_total_match:
        quantite = _safe_float(qty_total_match.group(1))
        total_ligne = _safe_float(qty_total_match.group(2))
        rows[0]["quantite"] = quantite
        rows[0]["total_ligne"] = total_ligne
        if quantite and total_ligne and quantite != 0:
            rows[0]["prix_unitaire"] = round(total_ligne / quantite, 6)

    return rows
