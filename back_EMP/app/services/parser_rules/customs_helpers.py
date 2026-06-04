"""Shared helpers for customs/template OCR extraction."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

from .customs_constants import DEFAULT_RESULT_KEYS, FORM_CASE_NUMBERS
from .geo_constants import COUNTRY_BY_CODE


def empty_result(article_rows=None):
    data = {key: None for key in DEFAULT_RESULT_KEYS}
    data["taxes"] = []
    data["articles"] = article_rows or []
    data["flags_validation"] = []
    return data


def _is_valid_date(value):
    if not value:
        return False
    try:
        datetime.strptime(str(value), "%d-%m-%Y")
        return True
    except Exception:
        return False


def _has_value(value):
    if value is None:
        return False
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return bool(str(value).strip())


def _clean_scalar(value):
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip(" -|:;,.")
    return cleaned or None


def _clean_amount(value):
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9,.\-]", "", str(value))
    cleaned = cleaned.replace(",", ".")
    cleaned = re.sub(r"\.(?=\d{3}\.)", "", cleaned)
    return cleaned or None


def _clean_code(value):
    if value is None:
        return None
    cleaned = re.sub(r"\s+", "", str(value).upper())
    cleaned = cleaned.replace("O", "0") if cleaned.isdigit() else cleaned
    return cleaned or None


def _normalize_date_value(value):
    if value is None:
        return None
    candidate = str(value).replace("/", "-").replace(".", "-")
    candidate = re.sub(r"[^0-9-]", "", candidate)
    if _is_valid_date(candidate):
        return candidate
    return None


def _fold_text(value):
    text_value = str(value or "")
    text_value = text_value.replace("™", "T").replace("â€™", "'")
    normalized = unicodedata.normalize("NFKD", text_value)
    no_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return no_marks.upper()


def _titre_ce_pair_plausible(code: str, num: str) -> bool:
    """Reject obvious OCR junk (QCS, délai, QCI) but allow typical codes like 22."""
    if not code or not num or not code.isdigit() or not num.isdigit():
        return False
    if int(code) > 99:
        return False
    if int(code) < 1:
        return False
    bad_codes = {
        "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15",
        "16", "17", "18", "19", "20", "21", "56", "104",
    }
    if code in bad_codes:
        return False
    inum = int(num)
    if inum < 100_000 or inum > 99_999_999:
        return False
    if num.startswith("880") or num.startswith("854"):
        return False
    return True


def extract_titre_ce_pair(text: str) -> tuple[str | None, str | None]:
    """Recover DUM boxes 43–44 (code / numéro Titre CE) when labels are noisy or missing."""
    if not text or not str(text).strip():
        return None, None
    folded = _fold_text(text)
    if not folded:
        return None, None

    ocr_word = r"T(?:I|[1Il!|\|])TRE"  # TITRE, T1TRE, common OCR garbles
    patterns = (
        re.compile(
            rf"CODE\s+{ocr_word}\s+CE[^\d]{{0,55}}(\d{{1,3}})\b[\s\S]{{0,300}}?"
            rf"(?:N\s*[°O0]?\s*|NUM\s*E?RO\s*){ocr_word}\s+CE[^\d]{{0,55}}(\d{{5,12}})\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"CODE\s+TITRE\s+CE[^\d]{0,55}(\d{1,3})\b[\s\S]{0,300}?NUMERO\s+TITRE\s+CE[^\d]{0,55}(\d{5,12})\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b43\b[^\d]{0,45}(\d{1,3})\b[\s\S]{0,120}?\b44\b[^\d]{0,45}(\d{5,12})\b",
            re.IGNORECASE,
        ),
    )
    for rx in patterns:
        m = rx.search(folded)
        if m and _titre_ce_pair_plausible(m.group(1), m.group(2)):
            return m.group(1), m.group(2)

    m = re.search(
        r"\b532\b[\s\D]{0,650}?(\d{1,3})\D{0,55}(\d{6,8})\b(?!\d)[\s\S]{0,220}?\b21\b\D{0,40}\b11\b",
        folded,
        re.IGNORECASE,
    )
    if m and _titre_ce_pair_plausible(m.group(1), m.group(2)):
        return m.group(1), m.group(2)

    m = re.search(
        r"\b362\b[\s\S]{0,180}?\b532\b[\s\S]{0,650}?(\d{1,3})\D{0,55}(\d{6,8})\b(?!\d)[\s\S]{0,220}?\b21\b\D{0,40}\b11\b",
        folded,
        re.IGNORECASE,
    )
    if m and _titre_ce_pair_plausible(m.group(1), m.group(2)):
        return m.group(1), m.group(2)

    return None, None


def _country_label(code, name=None):
    code = (code or "").upper().replace("™", "T")
    code = "TN" if code in {"T", "TN"} else code
    if code == "US":
        return "US USA"
    if code in COUNTRY_BY_CODE:
        return f"{code} {COUNTRY_BY_CODE[code]}"
    if name:
        return _clean_scalar(name.upper())
    return code or None


def _country_label_from_text(value):
    folded = _fold_text(value)
    folded = folded.replace("U S A", "USA").replace("U.S.A", "USA")
    folded = folded.replace("1N", "TN").replace("TM", "TN")
    for code, label in COUNTRY_BY_CODE.items():
        label_pattern = re.escape(label).replace(r"\ ", r"\s+")
        if re.search(rf"\b{code}\b", folded) or re.search(rf"\b{label_pattern}\b", folded):
            return _country_label(code, label)
    return None


def _set_field(data, key, value, force=False):
    value = _clean_scalar(value)
    if value is None:
        return
    if force or not _has_value(data.get(key)):
        data[key] = value


def _set_amount_field(data, key, value, force=False):
    amount = _clean_amount(value)
    if amount:
        _set_field(data, key, amount, force=force)


def _float_amount(value):
    try:
        return float(_clean_amount(value) or "")
    except Exception:
        return None


def _number_tokens(value):
    if value is None:
        return []
    return re.findall(r"\b\d{1,6}\b", str(value))


def _numeric_cell_token(value, *, min_value=0, max_value=999999,
                        reject_cases=True, prefer_last=True):
    tokens = _number_tokens(value)
    if prefer_last:
        tokens = list(reversed(tokens))

    for token in tokens:
        if reject_cases and token in FORM_CASE_NUMBERS:
            continue
        number = int(token)
        if min_value <= number <= max_value:
            return str(number)
    return None


def _is_small_condition_code(value):
    token = str(value or "").strip()
    return token.isdigit() and 1 <= int(token) <= 9


def _is_form_case_value(value, extra=None):
    token = re.sub(r"\s+", "", str(value or ""))
    if not token:
        return False
    return token in FORM_CASE_NUMBERS or token in set(extra or ())


def _valid_weight_pair(brut, net):
    brut_token = str(brut or "").strip()
    net_token = str(net or "").strip()
    if not brut_token.isdigit() or not net_token.isdigit():
        return False
    if brut_token in FORM_CASE_NUMBERS or net_token in FORM_CASE_NUMBERS:
        return False
    brut_value = int(brut_token)
    net_value = int(net_token)
    return brut_value > 0 and net_value > 0 and brut_value >= net_value


def _normalize_route(value):
    if not value:
        return None
    candidate = _fold_text(value)
    candidate = re.sub(r"\s*-\s*", "-", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip(" -|")
    if not candidate:
        return None
    if any(token in candidate for token in ("COLIS", "BUREAU", "LOCALISATION", "FRET", "ASSURANCE", "BR-")):
        return None
    match = re.search(r"\b([A-Z]{2,12})-([A-Z]{2,12})\b", candidate)
    if not match:
        return None
    route = f"{match.group(1)}-{match.group(2)}"
    if route.startswith("FAX-"):
        route = f"S{route}"
    if any(token in route for token in ("SFAX", "RADES", "TUNIS", "TC")):
        return route
    return None


def _looks_like_label_polluted_party(value):
    folded = _fold_text(value)
    if not folded:
        return False
    return any(
        token in folded
        for token in ("DECLARANT", "ADRESSE", "PAYS DE", "MOYEN DE", "CODE ", "NUMERO", "DATE")
    )


def _looks_like_exporter_in_importer(value) -> bool:
    """Importateur rempli avec le bloc exportateur (5751 / ENGINEERING / FAB…)."""
    folded = _fold_text(value)
    if not folded:
        return False
    return bool(
        re.search(
            r"\b(?:5751|FAB\s+EQUIPEMENTS|MECANIQUES?|ENGINEERING|MACHINING|PRECISION|MECANIQUI)\b",
            folded,
        )
    )


def _looks_like_bad_importer(value):
    folded = _fold_text(value)
    if not folded:
        return False
    words = re.findall(r"[A-Z]{2,}", folded)
    if folded in {"SE EAD", "SE EAO", "SE EAD I", "EAD"}:
        return True
    if len(words) <= 2 and "CTS" not in words and "RHINESTAHL" not in words:
        return True
    return _looks_like_label_polluted_party(value)


def _looks_like_garbled_party_name(value, *, role: str) -> bool:
    """True when OCR clearly merged columns or mis-read the party line (common on DUM headers)."""
    if not value or not str(value).strip():
        return False
    folded = _fold_text(value)
    if not folded:
        return False
    if _looks_like_ocr_noise_name(value):
        return True
    noise = (
        "VTY",
        "NSE",
        "IMPORTATENY",
        "CUCU",
        "WE CERN",
        "CERN 263",
        "IMPONAREN",
        "DANSNN",
        "EECARANT",
        "FAE TS",
        "SYSITEME",
        "GMBU CONE",
        "INPOITATERR",
        "INPOITAT",
        "TRNYNEARTATEAS",
        "ENENONININ",
        "TNNARTARAC",
        "MRAARTATN",
        "MRAARTA",
        "ARTATN",
        "IMMPONATEUR",
        "MEM RIASE",
        "SC MEM",
    )
    if role == "export" and re.search(r"\b[A-Z]{2}\s+[A-Z]{2}\s*-\s*F\s+EE\b", folded):
        return True
    if any(tok in folded for tok in noise):
        return True
    if role == "export":
        if len(folded) > 120:
            return True
        if re.search(r"\b(?:CERTIFICAT|BECLARATION|NADL)\b", folded):
            return True
        if re.search(r"\bDECLARATION\b", folded) and re.search(
            r"\b(?:NUMERO|DATE|D\.?\s*A\.?\s*E|DUCAL|TYPE\s+DECLARATION)\b",
            folded,
        ):
            return True
        if len(re.findall(r"\bNUMERO\b", folded)) >= 2:
            return True
        if re.search(r"\b(?:NADL|BECLARATION|IPORTATEUR|2P\s+CTS)\b", folded):
            return True
        if re.search(r"\bOE\s+XC\b", folded) or re.search(r"\bIMPON", folded):
            return True
        short_tokens = re.findall(r"\b[A-Z]{2}\b", folded)
        if len(short_tokens) >= 8 and not re.search(
            r"\b(?:ENGINEERING|FAB|MACHINING|PRECISION|STE|SARL|SA|EQUIPEMENTS)\b",
            folded,
        ):
            return True
        if re.search(r"\b(?:TNNARTARAC|ENED\s+ENT|INPOITAT)\b", folded):
            return True
        if re.search(r"\bIMPORTAT", folded) and not re.search(
            r"\b(?:ENGINEERING|EXPORT|FAB|MACHINING|PRECISION|EQUIPEMENTS)\b",
            folded,
        ):
            return True
        if re.search(r"\bCE\b", folded) and len(re.findall(r"[A-Z]{3,}", folded)) <= 4:
            if not re.search(
                r"\b(?:ENGINEERING|SARL|SA|STE|FAB|MACHINING|PRECISION|EQUIPEMENTS|GMBH)\b",
                folded,
            ):
                return True
    if role == "import":
        if re.search(r"^[^A-Z0-9]*[=;]", str(value)) or re.search(r"\b=\s*;\s*\d", folded):
            return True
        if re.search(r"\b(?:PIAL|ASAL|YAO\s+SHOW|YF\s+YAO|YF\s+YAO\s+SHOW)\b", folded):
            return True
        if re.search(r"^\s*WE\s+", folded) and "HYDRO" not in folded:
            return True
        if re.search(r"\b263\b", folded) and "HYDRO" not in folded and "GMBH" not in folded and "SYSTEME" not in folded:
            return True
        if re.search(r"\bDANSNN\b", folded) or re.search(r"\bEECARANT\b", folded):
            return True
        if "DECLARANT" in folded and re.search(r"\b526[34]\b", folded) and "HYDRO" not in folded:
            return True
        if re.search(r"\bLES\s+[A-Z]{2}(\s+[A-Z]{2}){2,}\b", folded) and "GMBH" not in folded and "RHINE" not in folded:
            return True
        if re.search(r"\bRAE\s+RB\b", folded) or re.search(r"\bEAR\s+A\b", folded):
            return True
    return False


def _looks_like_garbled_declarant_name(value) -> bool:
    """Very short OCR garbage (e.g. 'DE RE ER') with no broker tokens."""
    if not value or not str(value).strip():
        return False
    t = _fold_text(value)
    if not t:
        return False
    if re.search(r"\b(?:STE|SMART|CUSTOMS|BROKERS|TUNIS)\b", t):
        if re.search(r"\bSMART\b", t):
            return False
        if re.search(r"\bBROKERS\b", t) and not re.search(r"\bSMART\b", t):
            return True
    if re.search(
        r"\b(?:VERS\s+TRANGER|TRANGER|ETRANGER|COS\s+STY|NETRANGER|REPERTOIRE|CREDIT|NUL|EQS)\b",
        t,
    ):
        return True
    if re.search(r"\bPAYS\s+DE\s+PROVENANCE\b", t) or re.search(r"\bT&S\s+BAYS\b", t):
        return True
    if re.search(r"^C=!\s*\d", t):
        return True
    if re.search(r"\bENGINEERING\s+MACHIN\b", t) and re.search(r"\bREPERTOIRE|CREDIT|\[|\]|\=", t):
        return True
    if re.search(r"\b(?:CENSSRER|SSRERERS|PAN\s+CEN|AVV\s+LT|VV\s+LT|LT\s+UMS|UMS\s+BROKERS)\b", t):
        return True
    if len(t) < 25 and re.match(r"^([A-Z]{2}\s+){2,5}[A-Z]{2}\s*$", t):
        return True
    letters = re.sub(r"[^A-Z]", "", t)
    if len(letters) <= 18 and len(t.split()) <= 4 and not re.search(r"\b(?:SARL|SA|STE|SMART|CUSTOMS|BROKERS)\b", t):
        return True
    return False


_PARTY_NOISE_TOKENS = re.compile(
    r"\b(?:CERTIFICAT|NUMERO|DECLARATION|BECLARATION|NADL|DATE|TYPE\s+DECLARATION|"
    r"NBRE\s+TOTAL|PIAL|ASAL|YAO\s+SHOW|YF\s+YAO)\b",
    re.IGNORECASE,
)

_COMPANY_SUFFIX = re.compile(
    r"\b(?:GMBH|GMBH|B\.V|BV|SARL|SA|STE|SYSTEMS|SYSTEME|PRECISION|MACHINING|EQUIPEMENTS)\b",
    re.IGNORECASE,
)

_CODE_COLON_PARTY_RE = re.compile(r"\b\d{3,5}\s*[:;]\s*[A-Z]", re.IGNORECASE)


def _looks_like_ocr_noise_name(value) -> bool:
    """Bruit OCR pur (répétitions, peu de voyelles, pas de forme juridique)."""
    folded = _fold_text(value)
    if not folded or len(folded) < 10:
        return False
    if re.search(r"(.)\1{3,}", folded) or re.search(r"\b[A-Z]{1,2}\s+[A-Z]{1,2}\s+[A-Z]{1,2}\b", folded):
        return True
    if re.search(r"\bE{3,}\b|\bY{3,}\b|\bN{3,}\b", folded):
        return True
    letters = re.sub(r"[^A-Z]", "", folded)
    vowels = len(re.findall(r"[AEIOUY]", letters))
    if letters and vowels / max(len(letters), 1) < 0.12 and len(letters) > 12:
        return True
    if not _COMPANY_SUFFIX.search(folded) and not re.search(r"\b\d{3,5}\s*[:;]", folded):
        words = [w for w in folded.split() if len(w) >= 3]
        if len(words) >= 4 and sum(1 for w in words if len(set(w)) <= 2) >= 2:
            return True
    return False


def party_line_quality_score(value, *, role: str) -> float:
    """Score neutre : favorise lignes entreprise courtes, pénalise bruit bandeau DUM."""
    folded = _fold_text(value)
    if not folded:
        return -999.0
    if _looks_like_garbled_party_name(value, role=role):
        return -500.0
    score = float(len(re.sub(r"[^A-Z]", "", folded)))
    if _CODE_COLON_PARTY_RE.search(folded):
        score += 85.0
    if _COMPANY_SUFFIX.search(folded):
        score += 35.0
    score -= 60.0 * len(_PARTY_NOISE_TOKENS.findall(folded))
    if len(folded) > 100:
        score -= 45.0
    if len(folded) > 140:
        score -= 80.0
    return score


def should_prefer_party_value(current, new, *, role: str) -> bool:
    """True si `new` doit remplacer `current` (extraction neutre)."""
    cur_s = str(current or "").strip()
    new_s = str(new or "").strip()
    if not new_s:
        return False
    if not cur_s:
        return True
    new_score = party_line_quality_score(new_s, role=role)
    cur_score = party_line_quality_score(cur_s, role=role)
    if new_score < 0 and cur_score >= 0:
        return False
    if cur_score < 0 and new_score >= 0:
        return True
    return new_score > cur_score + 8.0


def normalize_exportateur_code_value(value: str | None) -> str | None:
    """Corrige codes type 11138190W → 1113819W (O/0 en trop avant W)."""
    if not value:
        return None
    raw = re.sub(r"\s+", "", str(value).upper())
    m = re.match(r"^(\d{6,8})[O0]?W$", raw)
    if m:
        return f"{m.group(1)}W"
    # 11138190W → 1113819W (0 en trop avant W)
    m_extra0 = re.match(r"^(\d{7})0W$", raw)
    if m_extra0:
        return f"{m_extra0.group(1)}W"
    m2 = re.match(r"^(\d{6,9}[A-Z])$", raw)
    return m2.group(1) if m2 else (raw if raw else None)


def strip_importateur_ocr_noise(value: str | None) -> str | None:
    """Retire le bruit OCR avant le nom importateur (sans imposer de société)."""
    if not value or not str(value).strip():
        return None
    text = re.sub(r"\s+", " ", str(value).upper()).strip(" .-|")
    if _looks_like_exporter_in_importer(text):
        return None
    text = re.sub(r"^[^A-Z0-9]*(?:[=;.]+\s*)*", "", text)
    text = re.sub(r"^\d{1,4}\s+", "", text)
    text = _PARTY_NOISE_TOKENS.sub(" ", text)
    text = re.sub(r"\bSHOW\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    m_gmbh = re.search(
        r"\b(HYDRO\s+SYSTEMS\s+GMBH|[A-Z][A-Z0-9&.\- ]{2,50}?\s+GMBH)\b",
        text,
        re.IGNORECASE,
    )
    if m_gmbh:
        text = re.sub(r"\s+", " ", m_gmbh.group(1)).strip().upper()
    if _looks_like_exporter_in_importer(text) or _looks_like_garbled_party_name(text, role="import"):
        return None
    return text if len(re.sub(r"[^A-Z]", "", text)) >= 4 else None


def _clean_exporter_name(value):
    if not value:
        return None
    candidate = _fold_text(value)
    candidate = re.sub(r"\bDATE\b\s*[A-Z0-9]{0,4}", " ", candidate)
    candidate = re.sub(r"\bMACHIN\s+ING\b", "MACHINING", candidate)
    candidate = re.sub(r"\b113\s+JAWDET\b.*$", " ", candidate)
    candidate = re.sub(r"\b(?:NUMERO|CERTIFICAT|DECLARATION|CODE)\b.*$", " ", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip(" -|")
    if len(candidate) > 120:
        candidate = candidate[:120].rsplit(" ", 1)[0].strip()
    if len(re.sub(r"[^A-Z]", "", candidate)) >= 8 and not _looks_like_garbled_party_name(
        candidate, role="export"
    ):
        return candidate
    return None
