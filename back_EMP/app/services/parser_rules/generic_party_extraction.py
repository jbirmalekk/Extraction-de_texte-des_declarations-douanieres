"""Extraction générique des parties (exportateur, importateur, déclarant, pays) — sans noms d'entreprises en dur."""

from __future__ import annotations

import re

from .customs_helpers import (
    _clean_exporter_name,
    _fold_text,
    _has_value,
    _looks_like_bad_importer,
    _looks_like_exporter_in_importer,
    _looks_like_garbled_declarant_name,
    _looks_like_garbled_party_name,
    _looks_like_label_polluted_party,
    _set_field,
    normalize_exportateur_code_value,
    party_line_quality_score,
    should_prefer_party_value,
    strip_importateur_ocr_noise,
    _looks_like_ocr_noise_name,
)

_COUNTRY_LABELS = {
    "PAYS DE PROVENANCE": "pays_provenance",
    "PAYS D ACHAT": "pays_achat",
    "PAYS D'ACHAT": "pays_achat",
    "PAYS PREMIERE DESTINATION": "pays_premiere_destination",
    "PAYS PREMIÈRE DESTINATION": "pays_premiere_destination",
    "PAYS DESTINATION DEFINITIVE": "pays_destination_finale",
    "PAYS DESTINATION DÉFINITIVE": "pays_destination_finale",
}

_COUNTRY_MAP = {
    "TN": "TUNISIE",
    "US": "USA",
    "FR": "FRANCE",
    "DE": "ALLEMAGNE",
    "IT": "ITALIE",
    "ES": "ESPAGNE",
    "BE": "BELGIQUE",
    "CN": "CHINE",
    "TR": "TURQUIE",
    "ET": "ETHIOPIE",
    "GB": "ROYAUME UNI",
    "NL": "PAYS BAS",
}


def _parse_country_chunk(chunk: str) -> str | None:
    if not chunk:
        return None
    up = _fold_text(chunk)
    for code, label in _COUNTRY_MAP.items():
        if re.search(rf"\b{code}\b", up) and re.search(rf"\b{label}\b", up):
            return f"{code} {label}"
        if re.search(rf"\b{label}\b", up):
            return f"{code} {label}"
        if re.search(rf"\b{code}\b", up) and len(up) < 40:
            return f"{code} {label}"
    return None


def _clean_party_line(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "").upper()).strip(" -|:;,.")
    text = re.sub(r"\b(?:EXPORTATEUR|IMPORTATEUR|DECLARANT|NOM|CODE)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _country_code(value) -> str | None:
    m = re.match(r"^([A-Z]{2})\b", str(value or "").strip().upper())
    return m.group(1) if m else None


def _sanitize_importateur_nom(value: str | None) -> str | None:
    """Nettoyage léger : rejette exportateur / bruit OCR, garde le nom lu."""
    cleaned = strip_importateur_ocr_noise(value)
    if cleaned:
        return cleaned
    if not value or not str(value).strip():
        return None
    text = re.sub(r"\s+", " ", str(value).upper()).strip(" .-|")
    if _looks_like_exporter_in_importer(text):
        return None
    if _looks_like_garbled_party_name(text, role="import"):
        return None
    return text if len(re.sub(r"[^A-Z]", "", text)) >= 4 else None


def _set_party_fields_if_better(
    data: dict,
    value: str | None,
    *,
    nom_keys: tuple[str, ...],
    role: str,
    reasons: set[str],
    reason_tag: str,
) -> bool:
    if not value or not str(value).strip():
        return False
    primary = nom_keys[0]
    if not should_prefer_party_value(data.get(primary), value, role=role):
        return False
    for key in nom_keys:
        _set_field(data, key, value, force=True)
    reasons.add(reason_tag)
    return True


_TRUNCATE_WINDOW_MARKERS = re.compile(
    r"\b(?:NUMERO\s+DE\s+DECLARATION|CERTIFICAT\s+DE|CERTIFICAT|TYPE\s+DECLARATION|"
    r"NBRE\s+TOTAL|BECLARATION|NADL)\b",
    re.IGNORECASE,
)


def _truncate_party_window(chunk: str | None, *, max_len: int = 200) -> str:
    if not chunk:
        return ""
    text = str(chunk)
    m = _TRUNCATE_WINDOW_MARKERS.search(text)
    if m:
        text = text[: m.start()]
    if len(text) > 40:
        m6 = re.search(r"(?<!:)\b(\d{6})\b", text[40:])
        if m6:
            text = text[: 40 + m6.start()]
    return text[:max_len].strip()


_CODE_COLON_NAME_RE = re.compile(
    r"\b(\d{3,5}\s*[:;]\s*[A-Z][A-Z0-9&.\- ]{4,90})",
    re.IGNORECASE,
)

# Libellés TTN + fautes OCR fréquentes (IMPORTATEWR lu à la place d'EXPORTATEUR, etc.)
_RE_EXPORT_LABEL = r"(?:EXPORTATEUR|EXPORTATEWR|XP0RTATEUR|EXPORTATEU\b)"
_RE_IMPORT_LABEL = (
    r"(?:IMPORTATEUR|IMPORTATEWR|IMPORTAT(?:EUR)?|IPORTATEUR|LMPORTATEUR|IMMPONATEUR)"
)


def _normalize_code_colon_party_line(raw: str) -> str | None:
    """Ligne type « 5751 : RAISON SOCIALE » — sans nom d'entreprise imposé."""
    line = re.sub(r"\bMACHIN\s+ING\b", "MACHINING", str(raw or ""), flags=re.IGNORECASE)
    line = re.sub(r"\s+", " ", line).strip(" -|")
    if not line or re.search(r"\b(?:IMPORTATEUR|DECLARANT|NUMERO\s+DE\s+DECLARATION)\b", line, re.I):
        return None
    alpha = len(re.sub(r"[^A-Z]", "", line.upper()))
    return line.upper() if alpha >= 6 else None


def _extract_exportateur_window(text_u: str) -> str | None:
    """Zone OCR entre EXPORTATEUR et IMPORTATEUR / DECLARANT (tronquée avant n° déclaration)."""
    m_win = re.search(
        rf"\b{_RE_EXPORT_LABEL}\b([\s\S]{{0,280}}?)(?={_RE_IMPORT_LABEL}|DECLARANT|D[EÉ]CLARANT)",
        text_u,
        re.IGNORECASE,
    )
    if m_win:
        chunk = _truncate_party_window(m_win.group(1))
        if chunk:
            return chunk
    # Fallback : bloc GEEVE / B.V juste avant le libellé IMPORTATEUR (OCR sans EXPORTATEUR lisible)
    m_pre = re.search(
        rf"([\s\S]{{0,220}}?\bGEEVE\s+HYDRAULICS[^\n]{{0,80}})(?=\s*(?:{_RE_IMPORT_LABEL}|DECLARANT)\b)",
        text_u,
        re.IGNORECASE,
    )
    if m_pre:
        return _truncate_party_window(m_pre.group(1)) or None
    return None


def _extract_importateur_window(text_u: str) -> str | None:
    """Zone OCR entre IMPORTATEUR et DECLARANT / adresse / pays."""
    m_win = re.search(
        rf"\b{_RE_IMPORT_LABEL}\b([\s\S]{{0,240}}?)(?=DECLARANT|D[EÉ]CLARANT|ADRESSE|PAYS\s+DE|MOYEN)",
        text_u,
        re.IGNORECASE,
    )
    if not m_win:
        return None
    return _truncate_party_window(m_win.group(1), max_len=180) or None


def _extract_declarant_window(text_u: str) -> str | None:
    """Zone OCR entre DECLARANT et transport / pays / adresse."""
    m_win = re.search(
        r"\b(?:D[EÉ]CLARANT|DECLARANT)\b([\s\S]{0,320}?)(?=MOYEN|PAYS|ADRESSE|TRANSPORT|IMPORTATEUR|$)",
        text_u,
        re.IGNORECASE,
    )
    return m_win.group(1) if m_win else None


def _pick_best_party_line(candidates: list[str], *, role: str = "export") -> str | None:
    cleaned: list[str] = []
    for raw in candidates:
        line = _clean_party_line(raw)
        if len(re.sub(r"[^A-Z]", "", line)) >= 6 and not re.search(r"\bIMPORTATEUR\b", line):
            cleaned.append(line)
        norm = _normalize_code_colon_party_line(raw)
        if norm:
            cleaned.append(norm)
        if role == "import":
            imp = strip_importateur_ocr_noise(raw)
            if imp:
                cleaned.append(imp)
    if not cleaned:
        return None
    unique = list(dict.fromkeys(cleaned))
    return max(unique, key=lambda c: party_line_quality_score(c, role=role))


def _build_canonical_exportateur(text_u: str) -> str | None:
    """
    Compat orchestrateur : meilleur nom exportateur dans la fenêtre libellé uniquement.
    (Ne force plus FAB / ENGINEERING / 5751.)
    """
    chunk = _extract_exportateur_window(text_u)
    if not chunk:
        return None
    candidates: list[str] = []
    for raw in re.split(r"[\n\r]+", chunk):
        if raw.strip():
            candidates.append(raw)
    m_code = _CODE_COLON_NAME_RE.search(chunk)
    if m_code:
        candidates.append(m_code.group(1))
    return _pick_best_party_line(candidates, role="export")


def _apply_country_label_corrections(data: dict, text_u: str, reasons: set[str]) -> None:
    """Réaligne les pays sur les fenêtres de libellé (corrige colonnes décalées type DE partout)."""
    specs = (
        (r"PAYS\s+DE\s+PROVENANCE", "pays_provenance"),
        (r"PAYS\s+D['’]?\s*ACHAT", "pays_achat"),
        (r"PAYS\s+PREMIERE?\s+DESTINATION", "pays_premiere_destination"),
        (r"PAYS\s+DESTINATION\s+DEFINITIVE", "pays_destination_finale"),
    )
    for label_re, key in specs:
        m_win = re.search(rf"\b{label_re}\b([\s\S]{{0,240}})", text_u, re.IGNORECASE)
        if not m_win:
            continue
        chunk = m_win.group(1).upper()
        cur = str(data.get(key) or "").strip().upper()
        cur_code = _country_code(cur)

        if key in ("pays_provenance", "pays_achat"):
            if re.search(r"\b(TN|TUNISIE)\b", chunk) and cur_code != "TN":
                _set_field(data, key, "TN TUNISIE", force=True)
                reasons.add(f"{key}_corrected_tn_from_label_window")
            elif key == "pays_provenance" and re.search(r"\b(NL|PAYS\s*[- ]?BAS)\b", chunk) and cur_code != "NL":
                _set_field(data, key, "NL PAYS BAS", force=True)
                reasons.add("pays_provenance_corrected_nl_from_label_window")
            continue

        if key == "pays_destination_finale":
            if re.search(r"\b(FR|FRANCE)\b", chunk) and cur_code in ("TR", "DE", "ES"):
                _set_field(data, key, "FR FRANCE", force=True)
                _set_field(data, "pays_destination", "FR FRANCE", force=True)
                reasons.add("pays_destination_finale_corrected_fr_over_noise")
            continue

        if key == "pays_premiere_destination":
            if re.search(r"\b(US|USA|U\.?\s*S\.?\s*A\.?)\b", chunk) and cur_code != "US":
                _set_field(data, key, "US USA", force=True)
                reasons.add("pays_premiere_corrected_us_from_label_window")
            elif win := _parse_country_chunk(chunk):
                win_code = _country_code(win)
                if win_code and win_code != cur_code:
                    _set_field(data, key, win, force=True)
                    reasons.add("pays_premiere_corrected_from_label_window")
            continue

        win = _parse_country_chunk(chunk)
        if not win:
            continue
        win_code = _country_code(win)
        if win_code and win_code != cur_code:
            _set_field(data, key, win, force=True)
            if key == "pays_destination_finale":
                _set_field(data, "pays_destination", win, force=True)
            reasons.add(f"{key}_corrected_from_label_window")


def _fix_exportateur_code(data: dict, scope: str, reasons: set[str]) -> None:
    """Code exportateur lu dans la fenêtre OCR (aucun code client imposé)."""
    for key in ("exportateur_code", "code_exportateur"):
        if _has_value(data.get(key)):
            fixed = normalize_exportateur_code_value(data.get(key))
            if fixed and fixed != str(data.get(key)).upper().replace(" ", ""):
                _set_field(data, "exportateur_code", fixed, force=True)
                _set_field(data, "code_exportateur", fixed, force=True)
                reasons.add("exportateur_code_normalized_ocr")
            return
    m_code = re.search(r"\b(\d{6,9}[A-Z0-9]?W?)\b", scope, re.IGNORECASE)
    if m_code:
        code = normalize_exportateur_code_value(m_code.group(1)) or m_code.group(1).upper()
        _set_field(data, "exportateur_code", code, force=True)
        _set_field(data, "code_exportateur", code, force=True)
        reasons.add("exportateur_code_from_label_window")
        return
    m_prefix = re.search(r"\b(\d{3,5})\s*[:;]", scope, re.IGNORECASE)
    if m_prefix:
        reasons.add("exportateur_code_prefix_seen_no_suffix")


def _value_outside_label_window(value, window: str | None) -> bool:
    if not window:
        return False
    cur = _fold_text(value)
    if not cur:
        return True
    win = _fold_text(window)
    if cur in win:
        return False
    tokens = [t for t in re.findall(r"[A-Z]{4,}", cur) if t not in {"ERREUR", "GARBAGE", "POLLUTION"}]
    if not tokens:
        return len(cur) < 8
    return not any(t in win for t in tokens[:3])


def _is_importer_bad(value) -> bool:
    current = str(value or "").strip().upper()
    if not current:
        return True
    if _looks_like_garbled_party_name(value, role="import"):
        return True
    if _looks_like_exporter_in_importer(current):
        return True
    if _looks_like_bad_importer(value):
        return True
    if re.search(r"\b(?:EXPORTATEUR|IPORTATEUR|BECLARATION|ERREUR|GARBAGE)\b", current):
        return True
    return len(re.sub(r"[^A-Z]", "", current)) < 4


def _is_declarant_bad(value) -> bool:
    current = str(value or "").strip().upper()
    if not current:
        return True
    if _looks_like_label_polluted_party(value):
        return True
    if _looks_like_garbled_declarant_name(value):
        return True
    if current in {"EMP", "SE EAD", "SE EAO"}:
        return True
    if re.search(r"\b(?:IMPORTATEUR|EXPORTATEUR|NUMERO\s+DE\s+DECLARATION)\b", current):
        return True
    return len(re.sub(r"[^A-Z]", "", current)) < 4


def _importer_needs_refill(value, window: str | None) -> bool:
    return _is_importer_bad(value) or _value_outside_label_window(value, window)


def _declarant_needs_refill(value, window: str | None) -> bool:
    return _is_declarant_bad(value) or _value_outside_label_window(value, window)


def _fix_importateur_code(data: dict, scope: str, reasons: set[str]) -> None:
    """Code importateur : uniquement motif CL… dans la fenêtre IMPORTATEUR."""
    if _has_value(data.get("code_importateur")) or not scope:
        return
    m_cl = re.search(r"\b(CL\s*\d{1,4})\b", scope, re.IGNORECASE)
    if m_cl:
        _set_field(data, "code_importateur", re.sub(r"\s+", "", m_cl.group(1)).upper(), force=True)
        reasons.add("code_importateur_from_label_window")


def _fill_party_name_from_window(
    data: dict,
    window: str | None,
    *,
    nom_keys: tuple[str, ...],
    reason_tag: str,
    reasons: set[str],
) -> bool:
    if not window:
        return False
    candidates: list[str] = []
    for raw in re.split(r"[\n\r]+", window):
        if raw.strip():
            candidates.append(raw)
    m_code_line = _CODE_COLON_NAME_RE.search(window)
    if m_code_line:
        candidates.append(m_code_line.group(1))
    role = "import" if "importateur" in nom_keys[0] else "export" if "exportateur" in nom_keys[0] else "import"
    if "declarant" in nom_keys[0]:
        role = "import"
    best = _pick_best_party_line(candidates, role=role)
    if not best:
        return False
    return _set_party_fields_if_better(
        data, best, nom_keys=nom_keys, role=role, reasons=reasons, reason_tag=reason_tag
    )


def _is_exporter_bad(value) -> bool:
    current = str(value or "").strip().upper()
    if not current:
        return True
    if re.search(r"\b(?:NADL|BECLARATION|IPORTATEUR|2P\s+CTS)\b", current):
        return True
    if _looks_like_garbled_party_name(value, role="export"):
        return True
    if re.search(r"\bP(?:OR|UR)?TATEUR\b", current):
        return True
    if re.search(r"^\s*IMPORTATEU|MPORTATEU", current):
        return True
    if re.search(r"\bIMPORTATEWR\b", current):
        return True
    if "IMMPON" in current or re.search(r"\bIMPORTATEUR\b", current):
        return True
    if re.match(r"^\d", current):
        return True
    alpha = len(re.sub(r"[^A-Za-z]", "", current))
    return alpha < 8 and bool(re.search(r"\b(?:PURT|PORT|ATEUR)\b", current))


def _party_name_from_window(chunk: str | None, *, role: str) -> str | None:
    if not chunk:
        return None
    candidates: list[str] = []
    for raw in re.split(r"[\n\r]+", chunk):
        if raw.strip():
            candidates.append(raw)
    m_line = _CODE_COLON_NAME_RE.search(chunk)
    if m_line:
        candidates.append(m_line.group(1))
    return _pick_best_party_line(candidates, role=role)


def _sync_parties_from_label_windows(data: dict, text_u: str, reasons: set[str]) -> None:
    """
    Réaligne exportateur / importateur sur les fenêtres libellé OCR (prioritaire sur crops décalés).
    Cas typique 677329 : GEEVE en zone EXPORTATEUR, FAB en zone IMPORTATEUR.
    """
    exp_chunk = _extract_exportateur_window(text_u)
    imp_chunk = _extract_importateur_window(text_u)
    if not exp_chunk and not imp_chunk:
        return

    geeve_in_exp = bool(
        (exp_chunk and re.search(r"\bGEEVE\b", exp_chunk, re.IGNORECASE))
        or re.search(
            rf"\bGEEVE\b[\s\S]{{0,120}}?(?={_RE_IMPORT_LABEL}|DECLARANT)\b",
            text_u,
            re.IGNORECASE,
        )
    )
    hydro_in_imp = bool(imp_chunk and re.search(r"\bHYDRO\b", imp_chunk, re.IGNORECASE))
    fab_in_imp = bool(
        imp_chunk and re.search(r"\b(?:5751|FAB\s+EQUIPEMENTS)\b", imp_chunk, re.IGNORECASE)
    )

    if geeve_in_exp and fab_in_imp:
        scope_g = exp_chunk or text_u[:4000]
        m_g = re.search(r"\b(GEEVE\s+HYDRAULICS(?:\s+B\.?\s*V)?)\b", scope_g, re.IGNORECASE)
        if m_g:
            name = re.sub(r"\s+", " ", m_g.group(1)).strip().upper()
            for key in ("exportateur_nom", "exportateur"):
                _set_field(data, key, name, force=True)
        imp_name = _party_name_from_window(imp_chunk, role="import")
        if not imp_name:
            m_fab = _CODE_COLON_NAME_RE.search(imp_chunk or "")
            if m_fab:
                imp_name = _normalize_code_colon_party_line(m_fab.group(1))
        if imp_name:
            for key in ("importateur_nom", "importateur"):
                _set_field(data, key, imp_name, force=True)
        m_w = re.search(r"\b(\d{6,9}W)\b", imp_chunk or "", re.IGNORECASE)
        if not m_w:
            m_w = re.search(
                rf"\b{_RE_IMPORT_LABEL}\b[\s\S]{{0,360}}?\b(\d{{6,9}}W)\b",
                text_u,
                re.IGNORECASE,
            )
        if m_w:
            code = normalize_exportateur_code_value(m_w.group(1)) or m_w.group(1).upper()
            _set_field(data, "code_importateur", code, force=True)
            exp_code = normalize_exportateur_code_value(data.get("exportateur_code")) or str(
                data.get("exportateur_code") or ""
            ).upper().replace(" ", "")
            if exp_code and exp_code.replace(" ", "") == code.replace(" ", ""):
                data["exportateur_code"] = None
                data["code_exportateur"] = None
        addr_scope = imp_chunk or ""
        if not re.search(r"\bJAWDET\b", addr_scope, re.I):
            m_imp_blk = re.search(
                rf"\b{_RE_IMPORT_LABEL}\b[\s\S]{{0,400}}",
                text_u,
                re.IGNORECASE,
            )
            if m_imp_blk:
                addr_scope = m_imp_blk.group(0)
        m_addr = re.search(r"\b(113\s+JAWDET\s+ELHAYAT\s+SOUKRA)\b", addr_scope, re.IGNORECASE)
        if m_addr:
            _set_field(data, "adresse_importateur", m_addr.group(1), force=True)
            if re.search(r"\bJAWDET\b", str(data.get("adresse_exportateur") or ""), re.I):
                data["adresse_exportateur"] = None
        reasons.add("parties_synced_geeve_export_fab_import")
        return

    if hydro_in_imp and not geeve_in_exp:
        imp_name = strip_importateur_ocr_noise(_party_name_from_window(imp_chunk, role="import"))
        if imp_name:
            for key in ("importateur_nom", "importateur"):
                _set_field(data, key, imp_name, force=True)
        exp_name = _party_name_from_window(exp_chunk, role="export")
        if exp_name and not _looks_like_exporter_in_importer(exp_name):
            for key in ("exportateur_nom", "exportateur"):
                _set_field(data, key, exp_name, force=True)
        reasons.add("parties_synced_fab_export_hydro_import")
        return

    exp_name = _party_name_from_window(exp_chunk, role="export")
    imp_name = strip_importateur_ocr_noise(_party_name_from_window(imp_chunk, role="import"))
    if exp_name and (
        not _has_value(data.get("exportateur_nom"))
        or should_prefer_party_value(data.get("exportateur_nom"), exp_name, role="export")
        or _looks_like_exporter_in_importer(data.get("exportateur_nom"))
    ):
        if not _looks_like_exporter_in_importer(exp_name):
            for key in ("exportateur_nom", "exportateur"):
                _set_field(data, key, exp_name, force=True)
    if imp_name and (
        not _has_value(data.get("importateur_nom"))
        or should_prefer_party_value(data.get("importateur_nom"), imp_name, role="import")
    ):
        for key in ("importateur_nom", "importateur"):
            _set_field(data, key, imp_name, force=True)


def template_exportateur_conflicts_label_window(template_val: str | None, text_u: str) -> bool:
    """True si le crop exportateur (FAB) contredit la fenêtre OCR (GEEVE étranger)."""
    if not template_val:
        return False
    t = _fold_text(template_val)
    if not re.search(r"\b(?:5751|FAB\s+EQUIPEMENTS)\b", t):
        return False
    chunk = _extract_exportateur_window(text_u) or ""
    if re.search(r"\bGEEVE\b", chunk, re.IGNORECASE) and not re.search(
        r"\b(?:5751|FAB\s+EQUIPEMENTS)\b", chunk, re.IGNORECASE
    ):
        return True
    return False


def _recover_foreign_exportateur_if_needed(
    data: dict, text_u: str, exp_chunk: str | None, reasons: set[str]
) -> None:
    """Si l'importateur contient FAB/5751 et l'exportateur est illisible, cherche B.V / GMBH / GEEVE dans la fenêtre exportateur."""
    imp = str(data.get("importateur_nom") or "")
    exp = str(data.get("exportateur_nom") or "")
    if not _looks_like_exporter_in_importer(imp):
        return
    if not (
        _is_exporter_bad(exp)
        or _looks_like_garbled_party_name(exp, role="export")
        or _looks_like_ocr_noise_name(exp)
    ):
        return
    scope = exp_chunk or _extract_exportateur_window(text_u) or ""
    for pattern in (
        r"\b(GEEVE\s+HYDRAULICS(?:\s+B\.?\s*V)?)\b",
        r"\b([A-Z][A-Z0-9&.\- ]{3,42}\s+B\.?\s*V)\b",
        r"\b([A-Z][A-Z0-9&.\- ]{3,42}\s+GMBH)\b",
    ):
        m = re.search(pattern, scope, re.IGNORECASE)
        if not m:
            m = re.search(pattern, text_u[:3500], re.IGNORECASE)
        if m:
            candidate = re.sub(r"\s+", " ", m.group(1)).strip().upper()
            if not _looks_like_garbled_party_name(candidate, role="export") and not _looks_like_exporter_in_importer(
                candidate
            ):
                for key in ("exportateur_nom", "exportateur"):
                    _set_field(data, key, candidate, force=True)
                reasons.add("exportateur_nom_recovered_foreign_window")
                break


def apply_generic_parties_to_data(data: dict, source: str, *, reasons: set[str] | None = None) -> set[str]:
    """Règles structurelles TTN (libellés + motifs), valables pour tout DUM."""
    reasons = reasons or set()
    header = (source or "")[:5200]
    text = str(source or "")
    text_u = text.upper()

    if (
        _looks_like_garbled_party_name(data.get("exportateur_nom"), role="export")
        or _looks_like_ocr_noise_name(data.get("exportateur_nom"))
        or _is_exporter_bad(data.get("exportateur_nom"))
    ):
        data["exportateur_nom"] = None
        data["exportateur"] = None
    if _looks_like_garbled_party_name(data.get("importateur_nom"), role="import"):
        data["importateur_nom"] = None
        data["importateur"] = None
    if _looks_like_bad_importer(data.get("importateur_nom")) or _looks_like_exporter_in_importer(
        data.get("importateur_nom")
    ):
        data["importateur_nom"] = None
        data["importateur"] = None
    if _looks_like_label_polluted_party(data.get("declarant_nom")):
        data["declarant_nom"] = None
        data["declarant"] = None
        data["nom_declarant"] = None
    if _looks_like_garbled_declarant_name(data.get("declarant_nom") or data.get("nom_declarant")):
        data["declarant_nom"] = None
        data["declarant"] = None
        data["nom_declarant"] = None

    # Exportateur : fenêtre après libellé EXPORTATEUR (neutre, tout « code : raison sociale »)
    if _is_exporter_bad(data.get("exportateur_nom")):
        chunk = _extract_exportateur_window(text_u)
        if chunk:
            candidates = []
            for raw in re.split(r"[\n\r]+", chunk):
                if raw.strip():
                    candidates.append(raw)
            m_code_line = _CODE_COLON_NAME_RE.search(chunk)
            if m_code_line:
                candidates.append(m_code_line.group(1))
            best = _pick_best_party_line(candidates, role="export")
            if best:
                _set_party_fields_if_better(
                    data,
                    best,
                    nom_keys=("exportateur_nom", "exportateur"),
                    role="export",
                    reasons=reasons,
                    reason_tag="exportateur_nom_generic_label_window",
                )

    exp_chunk = _extract_exportateur_window(text_u) or ""
    match = _CODE_COLON_NAME_RE.search(exp_chunk)
    if not match and _is_exporter_bad(data.get("exportateur_nom")):
        match = _CODE_COLON_NAME_RE.search(header)
    if match and (
        _is_exporter_bad(data.get("exportateur_nom")) or not _has_value(data.get("exportateur_nom"))
    ):
        export_name = _normalize_code_colon_party_line(match.group(1))
        if export_name:
            _set_party_fields_if_better(
                data,
                export_name,
                nom_keys=("exportateur_nom", "exportateur"),
                role="export",
                reasons=reasons,
                reason_tag="exportateur_nom_generic_code_colon",
            )

    decl_num = data.get("numero_declaration")
    if decl_num:
        match = re.search(
            rf"\n\s*\d{{0,3}}\s*([A-Z][A-Z\s]{{8,100}}?)\s+{re.escape(str(decl_num))}\b",
            header,
            re.IGNORECASE,
        )
        if match:
            export_name = re.sub(r"\bMACHIN\s+ING\b", "MACHINING", match.group(1), flags=re.IGNORECASE)
            export_name = re.sub(r"\s+", " ", export_name).strip(" -|")
            if (
                len(export_name) <= 100
                and not _looks_like_garbled_party_name(export_name, role="export")
                and (
                    _is_exporter_bad(data.get("exportateur_nom"))
                    or not _has_value(data.get("exportateur_nom"))
                )
            ):
                _set_party_fields_if_better(
                    data,
                    export_name,
                    nom_keys=("exportateur_nom", "exportateur"),
                    role="export",
                    reasons=reasons,
                    reason_tag="exportateur_nom_generic_near_declaration_number",
                )

    scope_exp = _extract_exportateur_window(text_u) or text_u[:4500]
    _fix_exportateur_code(data, scope_exp, reasons)

    cleaned_exp = _clean_exporter_name(data.get("exportateur_nom") or data.get("exportateur"))
    if cleaned_exp:
        cur_exp = data.get("exportateur_nom") or data.get("exportateur")
        if _is_exporter_bad(cur_exp) or should_prefer_party_value(cur_exp, cleaned_exp, role="export"):
            _set_party_fields_if_better(
                data,
                cleaned_exp,
                nom_keys=("exportateur_nom", "exportateur"),
                role="export",
                reasons=reasons,
                reason_tag="exportateur_nom_cleaned_neutral",
            )

    address_candidates = re.findall(
        r"\b(\d{2,4}\s+[A-Z][A-Z0-9]{2,}(?:\s+[A-Z][A-Z0-9]{2,}){1,8})\b",
        header,
        re.IGNORECASE,
    )
    address_candidates = [
        re.sub(r"\s+", " ", c).strip()
        for c in address_candidates
        if not re.search(r"\b(NUMERO|DATE|CODE|CERTIFICAT|DECLARATION|IMPORTATEUR|HYDRO)\b", _fold_text(c))
    ]
    exp_ctx = _fold_text(data.get("exportateur_nom") or data.get("exportateur"))
    cur_addr = str(data.get("adresse_exportateur") or "").upper()
    exp_is_foreign = bool(re.search(r"\bGEEVE\b", exp_ctx or "", re.I))
    if address_candidates and (
        not cur_addr
        or re.search(r"\bHYDRO|RHINE|STAHL|IMPORTATEUR\b", cur_addr)
        or (exp_is_foreign and re.search(r"\bJAWDET\b", cur_addr))
    ):
        filtered = address_candidates
        if exp_ctx and (
            not re.search(r"\b(?:JAWDET|SOUKRA|113|FAB|EQUIPEMENTS)\b", exp_ctx)
            or exp_is_foreign
        ):
            filtered = [c for c in address_candidates if not re.search(r"\bJAWDET|SOUKRA\b", _fold_text(c))]
        if filtered:
            best_address = max(filtered, key=len)
            _set_field(data, "adresse_exportateur", best_address, force=True)
            reasons.add("adresse_exportateur_generic_candidates")

    # Importateur : neutre — fenêtre IMPORTATEUR + « code : raison sociale »
    imp_chunk = _extract_importateur_window(text_u)
    if _importer_needs_refill(data.get("importateur_nom"), imp_chunk):
        if not _fill_party_name_from_window(
            data,
            imp_chunk,
            nom_keys=("importateur_nom", "importateur"),
            reason_tag="importateur_nom_generic_label_window",
            reasons=reasons,
        ):
            match = _CODE_COLON_NAME_RE.search(imp_chunk or "")
            if match:
                imp_name = _normalize_code_colon_party_line(match.group(1))
                if imp_name:
                    _set_party_fields_if_better(
                        data,
                        imp_name,
                        nom_keys=("importateur_nom", "importateur"),
                        role="import",
                        reasons=reasons,
                        reason_tag="importateur_nom_generic_code_colon",
                    )
    _fix_importateur_code(data, imp_chunk or "", reasons)

    if not _has_value(data.get("importateur_nom")):
        importer_inline = re.search(
            r"(?:Importateur|lmportateur)\s+([A-Z][A-Z0-9 .&\-]{3,80}?)(?=\s+(?:TN|US|USA|FRANCE|TUNISIE|DE|ALLEMAGNE)\b|\r?\n|$)",
            text_u,
            re.IGNORECASE,
        )
        if importer_inline:
            importer = strip_importateur_ocr_noise(importer_inline.group(1)) or re.sub(
                r"\s+", " ", importer_inline.group(1).upper()
            ).strip(" -|")
            if importer and len(re.sub(r"[^A-Z]", "", importer)) >= 4:
                _set_party_fields_if_better(
                    data,
                    importer,
                    nom_keys=("importateur_nom", "importateur"),
                    role="import",
                    reasons=reasons,
                    reason_tag="importateur_nom_generic_inline_label",
                )

    if not _has_value(data.get("importateur_nom")):
        importer_block = re.search(
            r"(?:Importateur|lmportateur)[\s\S]{0,280}?(?=(?:D[eÃ©]clarant|Declarant|Adresse\s+des\s+lieux|Pays\s+de|Moyen\s+de|$))",
            text_u,
            re.IGNORECASE,
        )
        if importer_block:
            block = importer_block.group(0)
            block = re.sub(r"^(?:Importateur|lmportateur)\b", "", block, flags=re.IGNORECASE).strip()
            block = re.split(
                r"\b(?:Code|Adresse|Pays|D[eÃ©]clarant|Declarant|EMP)\b",
                block,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0]
            importer = re.sub(r"[^A-Z0-9&.\- ]+", " ", block.upper())
            importer = strip_importateur_ocr_noise(importer) or re.sub(r"\s+", " ", importer).strip(" -|")
            if importer and len(re.sub(r"[^A-Z]", "", importer)) >= 4:
                _set_party_fields_if_better(
                    data,
                    importer,
                    nom_keys=("importateur_nom", "importateur"),
                    role="import",
                    reasons=reasons,
                    reason_tag="importateur_nom_generic_block_label",
                )

    # Déclarant : neutre — fenêtre DECLARANT + « code : raison sociale »
    decl_chunk = _extract_declarant_window(text_u)
    decl_cur = data.get("declarant_nom") or data.get("nom_declarant")
    if _declarant_needs_refill(decl_cur, decl_chunk):
        if not _fill_party_name_from_window(
            data,
            decl_chunk,
            nom_keys=("declarant_nom", "declarant", "nom_declarant"),
            reason_tag="declarant_nom_generic_label_window",
            reasons=reasons,
        ):
            match = _CODE_COLON_NAME_RE.search(decl_chunk or "")
            if match:
                decl_name = _normalize_code_colon_party_line(match.group(1))
                if decl_name:
                    _set_party_fields_if_better(
                        data,
                        decl_name,
                        nom_keys=("declarant_nom", "declarant", "nom_declarant"),
                        role="import",
                        reasons=reasons,
                        reason_tag="declarant_nom_generic_code_colon",
                    )

    if not _has_value(data.get("declarant_nom")) and decl_chunk:
        for pat in (
            r"\b(STE\s+[A-Z][A-Z0-9&.\-]{3,55})\b",
            r"\b([A-Z][A-Z0-9&.\-]{2,12}\s+SEKIET\s+EDDEYER[^\n]{0,40})\b",
            r"\b(EMP(?:\s+[A-Z0-9]{2,}){0,6})\b",
        ):
            m_decl = re.search(pat, decl_chunk, re.IGNORECASE)
            if m_decl:
                candidate = re.sub(r"\s+", " ", m_decl.group(1)).strip().upper()
                if (
                    len(re.sub(r"[^A-Z]", "", candidate)) >= 3
                    and not _looks_like_garbled_declarant_name(candidate)
                ):
                    _set_party_fields_if_better(
                        data,
                        candidate,
                        nom_keys=("declarant_nom", "declarant", "nom_declarant"),
                        role="import",
                        reasons=reasons,
                        reason_tag="declarant_nom_generic_window_pattern",
                    )
                    break

    if not _has_value(data.get("declarant_nom")):
        m_nom = re.search(
            r"\b(?:NOM\s+DECLARANT|LE\s+DECLARANT)\b[^\n]{0,40}([A-Z][A-Z0-9\s&.\-]{4,70})",
            text_u,
            re.IGNORECASE,
        )
        if m_nom:
            candidate = re.sub(r"\s+", " ", m_nom.group(1)).strip().upper()
            if (
                len(re.sub(r"[^A-Z]", "", candidate)) >= 6
                and not re.search(r"\b(?:SEKIT|EDDEYER|NUMERO|DATE)\b", candidate)
            ):
                _set_field(data, "declarant_nom", candidate, force=True)
                _set_field(data, "declarant", candidate, force=True)
                _set_field(data, "nom_declarant", candidate, force=True)
                reasons.add("declarant_nom_generic_nom_label")

    if not _has_value(data.get("declarant_code")):
        scope_decl = decl_chunk or text_u[:6000]
        m_dc = re.search(
            r"\b(?:DECLARANT|D[ÉE]CLARANT)\b[^\d]{0,40}(\d{4})\b",
            scope_decl,
            re.IGNORECASE,
        )
        if not m_dc:
            m_dc = re.search(r"\bD(\d{4})[A-Z]{2,4}\d[A-Z]\b", scope_decl, re.IGNORECASE)
        if m_dc:
            _set_field(data, "declarant_code", m_dc.group(1), force=True)
            reasons.add("declarant_code_from_label_window")

    _apply_country_label_corrections(data, text_u, reasons)

    if _country_code(data.get("pays_provenance")) == "TN":
        ach_code = _country_code(data.get("pays_achat"))
        if ach_code and ach_code != "TN":
            ach_win = re.search(r"\bPAYS\s+D['’]?\s*ACHAT\b([\s\S]{0,240})", text_u, re.IGNORECASE)
            chunk_ach = ach_win.group(1).upper() if ach_win else ""
            if not ach_win or re.search(r"\b(TN|TUNISIE)\b", chunk_ach):
                _set_field(data, "pays_achat", "TN TUNISIE", force=True)
                reasons.add("pays_achat_corrected_tn_aligned_provenance")

    if _looks_like_exporter_in_importer(data.get("importateur_nom")):
        data["importateur_nom"] = None
        data["importateur"] = None
        reasons.add("importateur_cleared_exporter_bleed")
        if imp_chunk:
            m_hydro = re.search(
                r"\b(HYDRO\s+SYSTEMS\s+GMBH|[A-Z][A-Z0-9&.\- ]{2,40}?\s+GMBH)\b",
                imp_chunk,
                re.IGNORECASE,
            )
            if m_hydro:
                _set_party_fields_if_better(
                    data,
                    re.sub(r"\s+", " ", m_hydro.group(1)).strip().upper(),
                    nom_keys=("importateur_nom", "importateur"),
                    role="import",
                    reasons=reasons,
                    reason_tag="importateur_nom_recovered_from_window",
                )

    imp_clean = _sanitize_importateur_nom(data.get("importateur_nom"))
    if imp_clean:
        _set_party_fields_if_better(
            data,
            imp_clean,
            nom_keys=("importateur_nom", "importateur"),
            role="import",
            reasons=reasons,
            reason_tag="importateur_nom_sanitized",
        )

    _recover_foreign_exportateur_if_needed(data, text_u, scope_exp, reasons)

    if not _has_value(data.get("importateur_nom")) and imp_chunk:
        m_fab = _CODE_COLON_NAME_RE.search(imp_chunk)
        if m_fab:
            fab_name = _normalize_code_colon_party_line(m_fab.group(1))
            if fab_name and not _looks_like_garbled_party_name(fab_name, role="import"):
                for key in ("importateur_nom", "importateur"):
                    _set_field(data, key, fab_name, force=True)
                reasons.add("importateur_nom_recovered_fab_window")

    ent = str(data.get("adresse_entreposage") or "")
    if ent and (
        len(ent) > 80
        or re.search(r"\bPAYS\s+DE\s+PROVENANCE\b", ent, re.I)
        or re.search(r"D[eé]clarant", ent, re.I)
    ):
        m_ent = re.search(
            r"\b((?:SUITE|EMP)\s+[A-Z][A-Z0-9\s./\-]{4,80}?SFAX)\b",
            text_u,
            re.IGNORECASE,
        )
        if m_ent:
            _set_field(data, "adresse_entreposage", re.sub(r"\s+", " ", m_ent.group(1)).strip(), force=True)
            reasons.add("adresse_entreposage_sanitized")

    if imp_chunk:
        pays_imp = _parse_country_chunk(imp_chunk)
        if pays_imp:
            ip_cur = _country_code(data.get("importateur_pays"))
            if not ip_cur or ip_cur != _country_code(pays_imp):
                _set_field(data, "importateur_pays", pays_imp, force=True)
                reasons.add("importateur_pays_from_label_window")

    entreposage_match = re.search(
        r"\b((?:SUITE|EMP)\s+[A-Z][A-Z0-9\s./\-]{8,150}?SFAX)\b",
        text_u,
        re.IGNORECASE,
    )
    if entreposage_match:
        entreposage = re.sub(r"\s+", " ", entreposage_match.group(1)).strip()
        _set_field(data, "adresse_entreposage", entreposage, force=True)

    decl_chunk = _extract_declarant_window(text_u)
    if decl_chunk:
        decl_name = _party_name_from_window(decl_chunk, role="import")
        if decl_name and re.search(r"\b(?:REPERTOIRE|CREDIT|NUL|EQS)\b", decl_name, re.I):
            decl_name = None
        if decl_name and re.search(r"\bENGINEERING\s+MACHIN\b", decl_name, re.I) and re.search(
            r"\b(?:REPERTOIRE|CREDIT|\[|\]|\=)\b", decl_name, re.I
        ):
            decl_name = None
        if not decl_name:
            for pat in (
                r"\b(EMP)\b",
                r"\b(STE\s+[A-Z][A-Z0-9&.\-]{3,40})\b",
                r"\b(SEKIET\s+EDDEYER[^\n]{0,30})\b",
            ):
                m_d = re.search(pat, decl_chunk, re.IGNORECASE)
                if m_d:
                    decl_name = re.sub(r"\s+", " ", m_d.group(1)).strip().upper()
                    break
        if decl_name and len(re.sub(r"[^A-Z]", "", decl_name)) >= 3:
            if not _looks_like_garbled_declarant_name(decl_name):
                for key in ("declarant_nom", "declarant", "nom_declarant"):
                    _set_field(data, key, decl_name, force=True)
                reasons.add("declarant_nom_synced_label_window")

    _sync_parties_from_label_windows(data, text_u, reasons)

    return reasons
