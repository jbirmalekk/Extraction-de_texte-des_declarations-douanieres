"""Build rich article dicts from a single OCR table row (merged cell texts)."""

from __future__ import annotations

import re
from typing import Any

from app.services.parser_rules.customs_helpers import extract_titre_ce_pair


def _norm_amount(s: str | None) -> str | None:
    if s is None:
        return None
    t = str(s).strip().replace(",", ".")
    return t if t else None


def _pick_hs(line: str) -> str | None:
    m = re.search(r"\b(\d{8,12})\b", line)
    return m.group(1) if m else None


def _pick_num_ligne(line: str) -> int | None:
    m = re.match(r"^\s*(\d{1,3})\b", line)
    if not m:
        return None
    try:
        v = int(m.group(1))
        return v if 1 <= v <= 999 else None
    except ValueError:
        return None


def enrich_article_row_from_line(
    row_text: str,
    *,
    page: int | None = None,
    code_hs: str | None = None,
    num_ligne: int | None = None,
) -> dict[str, Any]:
    """
    Parse one horizontal table row (all cells concatenated) into a canonical article record.

    Keys align with document-level marchandises fields where possible, plus ``page`` and ``source``.
    """
    line = re.sub(r"\s+", " ", (row_text or "")).strip()
    if not line:
        return {}

    hs = code_hs or _pick_hs(line)
    if not hs:
        return {}

    num = num_ligne if num_ligne is not None else _pick_num_ligne(line)
    upper = line.upper()

    out: dict[str, Any] = {
        "num_ligne": num,
        "code_hs": hs,
        "code_sh_ndp": hs,
        "source": "table_cells",
        "designation": None,
        "quantite": None,
        "unite": None,
        "prix_unitaire": None,
        "total_ligne": None,
        "code_pays_origine": None,
        "valeur_prise_en_charge": None,
        "code_qcs": None,
        "qcs": None,
        "pfn": None,
        "poids_brut": None,
        "poids_net": None,
        "qualite_fiscale": None,
        "regime_douanier": None,
        "imposition_speciale": None,
        "code_regime_precedent": None,
        "code_regime_financier": None,
        "code_delai": None,
        "code_oci": None,
        "code_titre_ce": None,
        "numero_titre_ce": None,
    }
    if page is not None:
        out["page"] = int(page)

    # --- Pays + valeur sous régime précédent (TN DE + montant) ---
    m_pcv = re.search(
        r"\b(\d{8,12})\s+(TN|DE|FR|IT|ES|BE|US|CN|TR|NL|GB)\s+(\d{1,12}(?:[.,]\d{3,4})?)\b",
        line,
        re.IGNORECASE,
    )
    if m_pcv and m_pcv.group(1) == hs:
        out["code_pays_origine"] = m_pcv.group(2).upper()
        out["valeur_prise_en_charge"] = _norm_amount(m_pcv.group(3))

    # --- Code QCS / QCS / PFN ---
    m_qcs = re.search(
        r"CODE\s+QCS[^\d]{0,14}(\d{1,3}).{0,22}\bQCS\b[^\d]{0,14}(\d{1,5}).{0,22}\bPFN\b[^\d]{0,14}(\d{1,12}(?:[.,]\d{1,4})?)",
        upper,
        re.IGNORECASE,
    )
    if m_qcs:
        out["code_qcs"] = m_qcs.group(1).zfill(2) if m_qcs.group(1).isdigit() and len(m_qcs.group(1)) <= 2 else m_qcs.group(1)
        out["qcs"] = m_qcs.group(2)
        out["pfn"] = _norm_amount(m_qcs.group(3))

    # --- Poids ---
    m_w = re.search(
        r"POIDS\s+BRUT(?:\s*\(KG\))?[^\d]{0,20}(\d{1,5}).{0,50}POIDS\s+NET(?:\s*\(KG\))?[^\d]{0,20}(\d{1,5})",
        upper,
        re.IGNORECASE,
    )
    if m_w:
        b, n = m_w.group(1), m_w.group(2)
        if b.isdigit() and n.isdigit() and int(b) >= int(n) > 0:
            out["poids_brut"] = b
            out["poids_net"] = n

    # --- Régimes douaniers (déclaré / précédent) ---
    m_reg = re.search(
        r"(?:REGIMES?\s+DOUANIERS?|R[ée]GIMES?\s+DOUANIERS?)[\s\S]{0,120}?"
        r"D[ée]CLAR[ée][^\d]{0,12}(\d{2,4})[\s\S]{0,80}?PREC[ée]DENT[^\d]{0,12}(\d{2,4})",
        upper,
        re.IGNORECASE,
    )
    if m_reg:
        out["regime_douanier"] = m_reg.group(1)
        out["imposition_speciale"] = m_reg.group(1)
        out["code_regime_precedent"] = m_reg.group(2)

    m_reg2 = re.search(r"\b(3\d{2})\s+(5\d{2})\b", line)
    if m_reg2 and not out.get("regime_douanier"):
        out["regime_douanier"] = m_reg2.group(1)
        out["imposition_speciale"] = m_reg2.group(1)
        out["code_regime_precedent"] = m_reg2.group(2)

    # --- Financier / délai / OCI ---
    m_fin = re.search(
        r"(?:REGLEMENT|REGIME)\s+FINANCIER[^\d]{0,12}(\d{1,2}).{0,30}(?:C\s*DELAI|CODE\s*DELAI|DELAI)[^\d]{0,12}(\d{1,2})",
        upper,
        re.IGNORECASE,
    )
    if m_fin:
        out["code_regime_financier"] = m_fin.group(1)
        out["code_delai"] = m_fin.group(2)
    m_oci = re.search(r"(?:CODE\s+)?(?:QCI|OCI)\b[^\d]{0,16}(\d{1,2})\b", upper, re.IGNORECASE)
    if m_oci:
        out["code_oci"] = m_oci.group(1)

    # --- Titre CE ---
    m_ce = re.search(
        r"CODE\s+TITRE\s+CE[^\d]{0,40}(\d{1,3})[\s\S]{0,200}?\bNUM[ÉE]RO\s+TITRE\s+CE[^\d]{0,40}(\d{5,12})\b",
        upper,
        re.IGNORECASE,
    )
    if m_ce:
        out["code_titre_ce"] = m_ce.group(1)
        out["numero_titre_ce"] = m_ce.group(2)
    else:
        tc, tn = extract_titre_ce_pair(line)
        if tc:
            out["code_titre_ce"] = tc
        if tn:
            out["numero_titre_ce"] = tn

    # --- Désignation (fragment libre hors étiquettes connues) ---
    frag = re.sub(
        r"(?i)\b(CODE\s+SH|NDP|QCS|PFN|POIDS|REGIME|DELAI|TITRE\s+CE|MARITIME|ROUTIER)\b",
        " ",
        line,
    )
    frag = re.sub(r"\d{8,12}", " ", frag)
    frag = re.sub(r"\b\d{1,3}\b", " ", frag)
    frag = re.sub(r"\s+", " ", frag).strip()
    if len(frag) >= 12 and re.search(r"[A-Za-zÀ-ÿ]{4,}", frag):
        out["designation"] = frag[:240]

    # --- Quantité / total (heuristique sur nombres restants) ---
    row_clean = re.sub(rf"\b{re.escape(hs)}\b", " ", line)
    nums = [
        float(t.replace(",", "."))
        for t in re.findall(r"\b\d+(?:[.,]\d+)?\b", row_clean)
        if re.search(r"[.,]", t) or (t.isdigit() and int(t) > 100)
    ]
    if len(nums) >= 2:
        out["quantite"] = nums[-2]
        out["total_ligne"] = nums[-1]
        if out["quantite"] and float(out["quantite"]) != 0:
            out["prix_unitaire"] = round(float(out["total_ligne"]) / float(out["quantite"]), 6)

    return out


def merge_cell_articles_with_regex_articles(
    cell_rows: list[dict],
    regex_rows: list[dict],
) -> list[dict]:
    """
    Prefer table cell rows (per page); fill missing fields from regex-built rows.
    Append regex-only rows when no cell row shares the same (num_ligne, code_hs).
    """
    if not cell_rows:
        return [dict(r) for r in (regex_rows or [])]

    merged = [dict(r) for r in cell_rows]

    def _same_article(a: dict, b: dict) -> bool:
        hs_a = a.get("code_hs") or a.get("code_sh_ndp")
        hs_b = b.get("code_hs") or b.get("code_sh_ndp")
        if not hs_a or hs_a != hs_b:
            return False
        na = a.get("num_ligne")
        nb = b.get("num_ligne")
        if isinstance(na, int) and isinstance(nb, int):
            return na == nb
        return True

    for ra in regex_rows or []:
        if not isinstance(ra, dict):
            continue
        target = None
        for m in merged:
            if _same_article(m, ra):
                target = m
                break
        if target is not None:
            for fld, val in ra.items():
                if fld in {"source", "page"}:
                    continue
                if target.get(fld) in (None, "") and val not in (None, ""):
                    target[fld] = val
        else:
            row = dict(ra)
            row.setdefault("source", "regex")
            merged.append(row)

    def _sort_key(a: dict) -> tuple:
        p = a.get("page")
        n = a.get("num_ligne")
        hs = a.get("code_hs") or a.get("code_sh_ndp") or ""
        return (p if isinstance(p, int) else 999, n if isinstance(n, int) else 999, hs)

    merged.sort(key=_sort_key)
    return merged
