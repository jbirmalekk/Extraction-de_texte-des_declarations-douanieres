"""Scoring and validation rules for parsed fields."""

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


def validate_fields(data: dict, *, types_valides: set[str], devises_valides: set[str]):
    score = 0
    total = 0
    flags = []

    def check(cond, label, weight=1):
        nonlocal score, total
        total += weight
        if cond:
            score += weight
        else:
            flags.append(label)

    num = data.get("numero_declaration")
    check(bool(num and re.fullmatch(r"\d{6}", str(num))), "numero_declaration", 3)

    date = data.get("date_declaration")
    check(bool(date and re.search(r"\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4}", str(date))), "date_declaration", 2)

    typ = str(data.get("type_declaration", "")).upper().replace(".", "").replace(" ", "")
    check(bool(typ and typ in types_valides), "type_declaration", 2)

    dev = str(data.get("devise", "")).upper().strip()
    check(bool(not dev or dev in devises_valides), "devise", 2)

    exp = data.get("exportateur_nom")
    check(bool(exp and len(re.sub(r"[^A-Za-z]", "", str(exp))) >= 5), "exportateur_nom", 2)

    imp = data.get("importateur_nom")
    check(bool(imp and len(str(imp).strip()) >= 5), "importateur_nom", 2)

    pb = _safe_float(data.get("poids_brut"))
    pn = _safe_float(data.get("poids_net"))
    if pb is not None and pn is not None:
        check(pb >= pn, "poids_brut_>=_poids_net", 1)
    else:
        total += 1

    check(bool(data.get("bureau_douane")), "bureau_douane", 1)

    cle = data.get("cle_authentification")
    check(bool(cle and re.fullmatch(r"D\d{2,6}[A-Z]{2,4}\d[A-Z]", str(cle).upper())), "cle_authentification", 1)

    pct = round(score / total * 100) if total > 0 else 0
    data["score_confiance"] = pct
    data["flags_validation"] = flags
    data["qualite"] = "HAUT" if pct >= 80 else ("MOYEN" if pct >= 50 else "BAS")
    return data
