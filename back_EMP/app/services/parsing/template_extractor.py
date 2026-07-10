import re
import logging

from app.services.ocr.recognition_service import recognize_detailed
from app.services.ocr.field_schema import FIELD_ZONES, validate_isolated_non_overlap
from app.services.ocr.dynamic_field_mapper import extract_dynamic_fields
from app.services.ocr.header_cell_ocr import extract_header_cell_fields
from app.services.ocr.zone_debug import save_zone_crop
from app.config import settings
from app.services.parser_rules.customs_helpers import extract_titre_ce_pair, _looks_like_garbled_party_name


_ZONE_CONFLICTS = validate_isolated_non_overlap()
logger = logging.getLogger("app.ocr.template_extractor")

FORM_CASE_NUMBERS = {
    "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15",
    "16", "17", "18", "19", "20", "21", "22", "23", "24",
    "30", "31", "32", "33", "34", "35", "36", "37", "38", "39",
    "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
    "50", "51", "52", "53", "54", "55", "56", "57", "58", "59",
    "60", "61", "62", "63", "64", "65", "66", "67",
}

FORBIDDEN_FIELD_TOKENS = re.compile(
    r"\b(?:DECLARANT|D[ÉE]CLARANT|CLARANT|CODE|N[°O]|NUMERO|REPERTOIRE|PERTOIRE|CREDIT|N\s*CREDIT)\b",
    re.IGNORECASE,
)
FORBIDDEN_EXPORTATEUR_NAME_TOKENS = re.compile(
    r"\b(?:EXPORTATEUR|ADRESSE|CODE|N[°O]|NUMERO|RUE|AV(?:ENUE)?|BP|SOUKRA|SFAX)\b",
    re.IGNORECASE,
)
FORBIDDEN_IMPORTATEUR_NAME_TOKENS = re.compile(
    r"\b(?:IMPORTATEUR|ADRESSE|CODE|N[°O]|NUMERO|RUE|AV(?:ENUE)?|BP)\b",
    re.IGNORECASE,
)
FORBIDDEN_DECLARANT_NAME_TOKENS = re.compile(
    r"\b(?:DECLARANT|D[ÉE]CLARANT|ADRESSE|REPERTOIRE|CODE|N[°O]|NUMERO|TRANSPORT|VERS|TRANGER|ETRANGER|ROUTIER|MARITIME)\b",
    re.IGNORECASE,
)
DECLARANT_NOISE_TOKENS = re.compile(
    r"\b(?:TYPE|DECLARATION|TOTAL|REGIME|FINANCIER|DELAI|OCI|GDT|QCS|PFN|ARTICLE|LIQUIDATION|TRANSIT|SOLLICITEE|PRECEDENT|TRANSPORT|NETRANGER|ANSPORT|VEHICULE|DOUANE|VERS|TRANGER|ETRANGER|FAT\s+I)\b",
    re.IGNORECASE,
)
STRICT_NUMERIC_ZONES = {
    "nombre_colis",
    "declarant_code",
    "num_repertoire",
    "exportateur_code",
    "code_importateur",
}

# Pixels (gauche, haut, droite, bas) — même idée que dynamic_field_mapper._ocr_with_retry
_ROI_EXPAND_MARGINS = (
    (0, 0, 0, 0),
    (10, 6, 10, 6),
    (20, 10, 20, 10),
    (35, 18, 35, 18),
)


def _crop_by_ratio(img, ratio):
    h, w = img.shape[:2]
    y1, y2, x1, x2 = ratio
    x1p = max(0, min(w, int(w * x1)))
    x2p = max(0, min(w, int(w * x2)))
    y1p = max(0, min(h, int(h * y1)))
    y2p = max(0, min(h, int(h * y2)))
    if x2p <= x1p:
        x2p = min(w, x1p + 1)
    if y2p <= y1p:
        y2p = min(h, y1p + 1)
    return img[y1p:y2p, x1p:x2p]


def _box_by_ratio(img, ratio):
    h, w = img.shape[:2]
    y1, y2, x1, x2 = ratio
    x1p = max(0, min(w, int(w * x1)))
    x2p = max(0, min(w, int(w * x2)))
    y1p = max(0, min(h, int(h * y1)))
    y2p = max(0, min(h, int(h * y2)))
    if x2p <= x1p:
        x2p = min(w, x1p + 1)
    if y2p <= y1p:
        y2p = min(h, y1p + 1)
    return x1p, y1p, x2p, y2p


def _recognize_zone_with_roi_expand(
    img,
    ratio,
    *,
    zone_psm: int,
    ocr_scale: float,
    field_name: str,
    critical: bool,
    fast_mode: bool,
):
    """
    OCR sur zone template avec Re-OCR sur ROI élargi (clamp image) si besoin.
    Choisit le meilleur candidat selon composite_score / business_valid (meta recognize_detailed).
    """
    h, w = img.shape[:2]
    x1, y1, x2, y2 = _box_by_ratio(img, ratio)
    margins = _ROI_EXPAND_MARGINS[:1] if fast_mode else _ROI_EXPAND_MARGINS

    best_details = None
    best_rank: tuple[float, bool, int] = (-1.0, False, -1)

    for ml, mt, mr, mb in margins:
        cx1 = max(0, min(w, int(x1 - ml)))
        cy1 = max(0, min(h, int(y1 - mt)))
        cx2 = max(0, min(w, int(x2 + mr)))
        cy2 = max(0, min(h, int(y2 + mb)))
        if cx2 <= cx1 or cy2 <= cy1:
            continue
        roi = img[cy1:cy2, cx1:cx2]
        details = recognize_detailed(
            roi,
            psm=zone_psm,
            ocr_scale=ocr_scale,
            field_name=field_name,
            critical=critical,
        )
        meta = details.get("meta") or {}
        biz = bool(meta.get("business_valid", False))
        comp = float(meta.get("composite_score", details.get("confidence") or 0.0))
        tlen = len((details.get("text") or "").strip())
        rank = (comp, biz, tlen)
        if rank > best_rank or best_details is None:
            best_rank = rank
            meta = dict(details.get("meta") or {})
            meta["roi_expand_margins"] = (ml, mt, mr, mb)
            meta["roi_expand_box"] = (cx1, cy1, cx2, cy2)
            best_details = {**details, "meta": meta}
        th = float(settings.OCR_CONFIDENCE_THRESHOLD)
        if biz and float(details.get("confidence") or 0.0) >= th:
            break

    if best_details is None:
        roi = _crop_by_ratio(img, ratio)
        return recognize_detailed(
            roi,
            psm=zone_psm,
            ocr_scale=ocr_scale,
            field_name=field_name,
            critical=critical,
        )
    return best_details


def _clean_text(value):
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip(" -|:;,.")
    return cleaned or None


def _number_tokens(value):
    if not value:
        return []
    return re.findall(r"\b\d{1,6}\b", str(value))


def _numeric_cell_value(value, *, min_value=0, max_value=999999,
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


def _first_amount(value):
    if not value:
        return None
    match = re.search(r"\b(\d{1,12}\s*[,.]\s*\d{3,8})\b", str(value))
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(1)).replace(",", ".")


def _amount_cell_value(value):
    """Montant type 58477.725 dans une cellule (case 49 FOB / Douane)."""
    if not value:
        return None
    text = re.sub(r"(?i)\b(?:FOB|DOUANE|DINARS|VALEUR)\b", " ", str(value))
    match = re.search(r"\b(\d{1,12}[.,]\d{3})\b", text)
    if match:
        return match.group(1).replace(",", ".")
    return _first_amount(value)


def _country_cell_value(value):
    if not value:
        return None
    text = str(value).upper()
    text = text.replace("U.S.A", "USA").replace("U S A", "USA")
    text = text.replace("1N", "TN").replace("TM", "TN")
    countries = {
        "TN": "TUNISIE",
        "US": "USA",
        "FR": "FRANCE",
        "DE": "ALLEMAGNE",
        "IT": "ITALIE",
        "ES": "ESPAGNE",
        "BE": "BELGIQUE",
        "CY": "CHYPRE",
        "CN": "CHINE",
        "TR": "TURQUIE",
        "NL": "PAYS BAS",
        "GB": "ROYAUME UNI",
        "PT": "PORTUGAL",
    }
    for code, label in countries.items():
        if re.search(rf"\b{code}\b", text) or re.search(rf"\b{label}\b", text):
            return f"{code} {label}"
    return None


def _clean_company_cell(value):
    if not value:
        return None
    text = str(value).upper()
    text = re.sub(r"\b(?:IMPORTATEUR|EXPORTATEUR|CODE|PAYS|USA|U\.?S\.?A\.?|TUNISIE)\b", " ", text)
    text = re.sub(r"[^A-Z0-9&.\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -|")
    if len(re.sub(r"[^A-Z]", "", text)) >= 4:
        return text
    return None


def _clean_declarant_cell(value):
    if not value:
        return None
    upper = str(value).upper()
    # Avoid promoting a pure address/location as declarant name.
    if re.search(r"\b(?:SEKIT|EDDEYER|RUE|AVENUE|SOUKRA|TUNIS|SFAX)\b", upper):
        return None
    text = re.sub(r"\b(?:DECLARANT|D[ÉE]CLARANT|REPERTOIRE|CODE)\b", " ", upper)
    text = re.sub(r"[^A-Z0-9&.\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -|")
    if len(re.sub(r"[^A-Z]", "", text)) >= 4:
        return text
    return None


def _clean_declarant_name_cell(value):
    if not value:
        return None
    text = str(value).upper()
    text = re.sub(r"\b(?:DECLARANT|D[ÉE]CLARANT|NOM)\b", " ", text)
    text = re.sub(r"[^A-Z0-9&.\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -|:;,.")
    if FORBIDDEN_DECLARANT_NAME_TOKENS.search(text):
        return None
    if re.search(r"\b(?:SFAX|TUNIS|SOUSSE|SEKIT|EDDEYER|RUE|AV(?:ENUE)?)\b", text):
        return None
    if re.search(r"\b(?:TRANGER|ETRANGER)\b", text) or re.search(r"\bVERS\s+I\b", text):
        return None
    if re.match(r"^\d{2,6}\b", text):
        return None
    if len(re.sub(r"[^A-Z]", "", text)) < 3:
        return None
    return text


def _clean_declarant_address_cell(value):
    if not value:
        return None
    text = str(value).upper()
    text = re.sub(r"\b(?:ADRESSE\s+DECLARANT|ADRESSE)\b", " ", text)
    text = re.sub(r"[^A-Z0-9&.\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -|:;,.")
    if re.search(r"\b(?:DECLARANT|REPERTOIRE)\b", text):
        return None
    if len(re.sub(r"[^A-Z]", "", text)) < 5:
        return None
    return text


def _clean_exporter_name_cell(value):
    if not value:
        return None
    if _looks_like_garbled_party_name(value, role="export"):
        return None
    text = str(value).upper()
    text = re.sub(r"\b(?:EXPORTATEUR|NOM|RAISON\s+SOCIALE)\b", " ", text)
    text = re.sub(r"^(?:IMPORTATEU[RL]?|LMPORTATEUR|MPORTATEU[RL]?)\b\s*", "", text)
    text = re.sub(r"^(?:\d{1,3}\s+)+", "", text)
    text = re.sub(r"^(?:TO|T0|2P)\s+", "", text)
    text = re.sub(r"^(?:EB|E8|8B)\s+", "", text)
    text = re.sub(r"\b\d{6,9}[A-Z]?\b", " ", text)
    text = re.sub(r"\b(?:NESTAHL|NEASTAHL|RHINESTAHL|STAHL\s+CTS)\b", " ", text)
    text = re.sub(r"\bMACHIN\s+ING\b", "MACHINING", text, flags=re.IGNORECASE)
    text = re.sub(r"[^A-Z0-9&.\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -|:;,.")
    text = re.sub(r"^\d{4}\s*:\s*FAB\s+", "", text, flags=re.IGNORECASE)
    if re.search(r"\bIMPORTATEUR\b", text):
        left = re.split(r"\bIMPORTATEUR\b", text, maxsplit=1)[0]
        left = re.sub(r"\s+", " ", left).strip(" -|:;,.")
        if len(re.sub(r"[^A-Z]", "", left)) >= 5:
            text = left
    if FORBIDDEN_EXPORTATEUR_NAME_TOKENS.search(text):
        return None
    # "PORTATEUR" alone is OCR noise from label context, not company name.
    if re.search(r"\bPORTATEUR\b", text) and not re.search(r"\b(?:ENGINEERING|MACHINING|FAB|EQUIPEMENTS)\b", text):
        return None
    if len(re.sub(r"[^A-Z]", "", text)) < 5:
        return None
    return text


def _extract_numeric_from_text(value, *, min_value=0, max_value=999999):
    if not value:
        return None
    tokens = re.findall(r"\b\d{1,8}\b", str(value))
    for token in reversed(tokens):
        number = int(token)
        if min_value <= number <= max_value:
            return str(number)
    return None


def _clean_exporter_address_cell(value):
    if not value:
        return None
    text = str(value).upper()
    if re.match(r"^\s*\d{1,3}\s+HYD", text):
        return None
    if re.search(r"\bHYDRO\s+SYSTEME\b", text) and "JAWDET" not in text and not re.search(r"\b113\b", text):
        return None
    if re.search(r"\bRHINE?\s*STAU?L\b", text) and not re.search(r"\b(?:JAWDET|SOUKRA|SFAX|TUNIS)\b", text):
        return None
    text = re.sub(r"\b(?:ADRESSE\s+EXPORTATEUR|ADRESSE)\b", " ", text)
    text = re.sub(r"[^A-Z0-9&.\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -|:;,.")
    if "EXPORTATEUR" in text:
        return None
    # Address should usually contain at least one digit (street number / code).
    if not re.search(r"\d", text):
        return None
    return text


def _clean_importer_name_cell(value):
    if not value:
        return None
    from app.services.parser_rules.customs_helpers import strip_importateur_ocr_noise

    cleaned_noise = strip_importateur_ocr_noise(value)
    if cleaned_noise:
        return cleaned_noise
    if _looks_like_garbled_party_name(value, role="import"):
        return None
    text = str(value).upper()
    text = re.sub(r"\b(?:IMPORTATEUR|NOM|RAISON\s+SOCIALE)\b", " ", text)
    text = re.sub(r"[^A-Z0-9&.\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -|:;,.")
    if FORBIDDEN_IMPORTATEUR_NAME_TOKENS.search(text):
        return None
    # If line starts with a number (zip/street), it is likely an address.
    if re.match(r"^\d{2,6}\b", text):
        return None
    if re.search(r"\b(?:GERMANY|DEUTSCHLAND|ALLEMAGNE|FRANCE|TUNISIE|ITALIE)\b", text):
        return None
    if re.search(r"\bENGINEERING\b", text) and re.search(r"\bMACHIN", text) and re.search(r"\bPRECISION\b", text):
        return None
    if re.search(r"\b(?:INEEPING|INGINEERING|INEE\s+PING|INEEP)\b", text, re.IGNORECASE):
        return None
    # Company names should not be mostly numeric.
    letters = len(re.sub(r"[^A-Z]", "", text))
    digits = len(re.sub(r"[^0-9]", "", text))
    if letters < 4 or digits > max(3, letters):
        return None
    return text


def _extract_importer_name_from_block(value):
    if not value:
        return None
    lines = [re.sub(r"\s+", " ", line).strip(" -|:;,.") for line in str(value).splitlines()]
    lines = [line for line in lines if line]
    for line in lines:
        up = line.upper()
        if "IMPORTATEUR" in up:
            continue
        if re.match(r"^\d{2,6}\b", up):
            continue
        if re.search(r"\b(?:GERMANY|ALLEMAGNE|TUNISIE|FRANCE|ITALIE)\b", up):
            continue
        if re.search(r"\b(?:GMBH|SARL|SA|SYSTEMS|TRADING|INDUSTR|EQUIPEMENTS)\b", up) and len(re.sub(r"[^A-Z]", "", up)) >= 6:
            return up
    return None


def _clean_importer_address_cell(value):
    if not value:
        return None
    text = str(value).upper()
    text = re.sub(r"\b(?:ADRESSE\s+IMPORTATEUR|ADRESSE)\b", " ", text)
    text = re.sub(r"[^A-Z0-9&.\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -|:;,.")
    if "IMPORTATEUR" in text:
        return None
    if re.search(r"\b(?:SUITE\s+DIVERS|SEKIT\s+EDDEYER)\b", text):
        return None
    # Address generally has street/zip number or explicit country token.
    if not (re.search(r"\d", text) or re.search(r"\b(?:GERMANY|DEUTSCHLAND|ALLEMAGNE|FRANCE|TUNISIE|ITALIE)\b", text)):
        return None
    return text


def _extract_direct_fields(raw):
    fields = {}
    reject_reasons = []

    text = "\n".join(v for v in raw.values() if v)
    country_hint_src = "\n".join(
        str(raw.get(k) or "")
        for k in ("block_conditions", "block_transport", "block_finances")
    )
    guided_declarant = _extract_guided_declarant_fields(text)
    guided_logistics = _extract_guided_logistics_fields(text)
    guided_article = _extract_guided_article_fields((raw.get("block_article_1") or "") + "\n" + text)
    guided_countries = _extract_guided_country_fields(country_hint_src + "\n" + text)

    number = re.search(r"\b(\d{6})\b", raw.get("numero_declaration", "") or "")
    if number:
        fields["numero_declaration"] = number.group(1)

    date = re.search(r"\b(\d{2}[\/\-.]\d{2}[\/\-.]\d{4})\b", raw.get("date_declaration", "") or "")
    if date:
        fields["date_declaration"] = date.group(1).replace("/", "-").replace(".", "-")
    certif = re.search(r"\bCERTIFICAT\s+DE\s+DECHARGE\b[^\d]{0,20}(\d{3,10})\b", text, re.IGNORECASE)
    if certif:
        fields["certificat_decharge"] = certif.group(1)

    decl_type = re.search(r"\b(EA|SE|EE|DUM|IM\d*|EX\d*|T1)\b", (raw.get("type_declaration", "") or "").upper())
    if decl_type:
        fields["type_declaration"] = decl_type.group(1)

    article_count = _numeric_cell_value(
        raw.get("nbre_articles"),
        min_value=1,
        max_value=99,
        prefer_last=True,
    )
    if article_count:
        fields["nbre_articles"] = article_count
        fields["nombre_articles"] = article_count

    colis = _numeric_cell_value(
        raw.get("nombre_colis"),
        min_value=1,
        max_value=999,
        prefer_last=True,
    )
    if colis:
        fields["nombre_colis"] = colis

    # Strong business fallback: prefer explicit "Nbre colis <n>" in liquidation block.
    liquidation_block = raw.get("block_liquidation", "") or ""
    colis_from_label = re.search(r"(?:Nbre|Nombre)\s*colis[^\d]{0,24}(\d{1,3})", liquidation_block, re.IGNORECASE)
    if colis_from_label:
        labeled_colis = colis_from_label.group(1)
        current = str(fields.get("nombre_colis") or "")
        if (not current) or (current.isdigit() and int(current) > 3 and labeled_colis.isdigit() and int(labeled_colis) <= 3):
            fields["nombre_colis"] = labeled_colis

    export_code = re.search(r"\b(\d{6,8}[A-Z])\b", raw.get("exportateur_code", "") or "", re.IGNORECASE)
    if export_code:
        fields["exportateur_code"] = export_code.group(1).upper()
        fields["code_exportateur"] = export_code.group(1).upper()

    export_area = raw.get("exportateur_area") or ""
    exporter_name_raw = raw.get("exportateur_nom") or export_area
    exporter_name = _clean_exporter_name_cell(exporter_name_raw)
    if exporter_name:
        fields["exportateur_nom"] = exporter_name
        fields["exportateur"] = exporter_name
    elif raw.get("exportateur_nom"):
        reject_reasons.append("exportateur_nom_rejected_label_pollution")

    exporter_address_raw = raw.get("adresse_exportateur")
    exporter_address = _clean_exporter_address_cell(exporter_address_raw)
    if exporter_address:
        fields["adresse_exportateur"] = exporter_address
    elif exporter_address_raw:
        reject_reasons.append("adresse_exportateur_rejected_invalid_address")

    importer_name_raw = raw.get("importateur_nom") or raw.get("importateur_area") or raw.get("block_importateur")
    importer_name = _clean_importer_name_cell(importer_name_raw)
    if not importer_name:
        importer_name = _extract_importer_name_from_block(raw.get("importateur_area") or raw.get("block_importateur"))
    imp_code_raw = raw.get("code_importateur") or ""
    m_cl = re.search(r"\b(CL\s*\d{1,4})\b", imp_code_raw, re.IGNORECASE)
    if m_cl:
        fields["code_importateur"] = re.sub(r"\s+", "", m_cl.group(1)).upper()

    pays_imp_cell = (raw.get("importateur_pays_cell") or "").strip()
    if pays_imp_cell:
        m_us = re.search(r"\b(US|USA|U\.?\s*S\.?\s*A\.?)\b", pays_imp_cell, re.IGNORECASE)
        if m_us:
            fields["importateur_pays"] = "US USA"

    if importer_name and not FORBIDDEN_FIELD_TOKENS.search(importer_name):
        fields["importateur_nom"] = importer_name
        fields["importateur"] = importer_name
    elif importer_name_raw:
        reject_reasons.append("importateur_nom_rejected_label_pollution")
        fields.pop("importateur_nom", None)
        fields.pop("importateur", None)

    importer_address_raw = raw.get("adresse_importateur")
    importer_address = _clean_importer_address_cell(importer_address_raw)
    if importer_address:
        fields["adresse_importateur"] = importer_address
    elif importer_address_raw:
        reject_reasons.append("adresse_importateur_rejected_invalid_address")

    entreposage = re.search(r"\b(EMP\s+[A-Z0-9\s]{8,100}?SFAX)\b", text, re.IGNORECASE)
    if entreposage:
        fields["adresse_entreposage"] = _clean_text(entreposage.group(1))

    decl_code = _numeric_cell_value(
        raw.get("declarant_code"),
        min_value=10,
        max_value=99999,
        reject_cases=False,
        prefer_last=True,
    )
    if decl_code and len(decl_code) in (2, 3, 4, 5):
        fields["declarant_code"] = decl_code

    repertoire_case = _numeric_cell_value(
        raw.get("num_repertoire"),
        min_value=1000,
        max_value=99999,
        reject_cases=False,
        prefer_last=True,
    )
    if not repertoire_case:
        repertoire_case = _numeric_cell_value(
            raw.get("declarant_code") or raw.get("declarant_nom") or raw.get("block_declarant"),
            min_value=1000,
            max_value=99999,
            reject_cases=False,
            prefer_last=True,
        )
    if repertoire_case:
        fields["num_repertoire"] = repertoire_case

    declarant_name_raw = raw.get("declarant_nom")
    declarant_name = _clean_declarant_name_cell(declarant_name_raw)
    if declarant_name and not FORBIDDEN_FIELD_TOKENS.search(declarant_name):
        fields["declarant_nom"] = declarant_name
        fields["declarant"] = declarant_name
        fields["nom_declarant"] = declarant_name
    elif declarant_name_raw:
        reject_reasons.append("declarant_nom_rejected_label_pollution")
        fields.pop("declarant_nom", None)
        fields.pop("declarant", None)
        fields.pop("nom_declarant", None)

    declarant_address_raw = raw.get("adresse_declarant")
    declarant_address = _clean_declarant_address_cell(declarant_address_raw)
    if declarant_address:
        fields["adresse_declarant"] = declarant_address
    elif declarant_address_raw:
        reject_reasons.append("adresse_declarant_rejected_invalid_address")

    # Legacy fallback from wide block: keeps compatibility if strict cells are empty.
    if not fields.get("declarant_nom") or not fields.get("adresse_declarant"):
        declarant_fallback = _clean_declarant_cell(raw.get("declarant_nom"))
        if declarant_fallback and not fields.get("declarant_nom"):
            fields["declarant_nom"] = declarant_fallback
            fields["declarant"] = declarant_fallback
            fields["nom_declarant"] = declarant_fallback

    # Template-aware rescue for declarant/repertoire/credit from noisy declarant block.
    declarant_block = " ".join(
        str(raw.get(k) or "")
        for k in ("declarant_nom", "adresse_declarant", "block_declarant", "block_final", "block_liquidation")
    ).upper()
    if not fields.get("num_repertoire"):
        m_rep = re.search(r"\bREPERTOIRE\b[^\d]{0,24}(\d{3,6})\b", declarant_block, re.IGNORECASE)
        if not m_rep:
            m_rep = re.search(r"\bDECLARANT\b[^\d]{0,40}(\d{3,6})\b", declarant_block, re.IGNORECASE)
        if m_rep:
            fields["num_repertoire"] = m_rep.group(1)
    if not fields.get("num_repertoire") and guided_declarant.get("num_repertoire"):
        fields["num_repertoire"] = guided_declarant["num_repertoire"]
    if not fields.get("numero_credit"):
        m_credit = re.search(r"\b(?:N|NUM|N[°O])\s*CREDIT\b[^\d]{0,24}(\d{3,10})\b", declarant_block, re.IGNORECASE)
        if m_credit:
            fields["numero_credit"] = m_credit.group(1)
    if not fields.get("numero_credit") and guided_declarant.get("numero_credit"):
        fields["numero_credit"] = guided_declarant["numero_credit"]
    if not fields.get("declarant_nom"):
        m_nom_decl = re.search(
            r"\b(?:NOM\s+DECLARANT|LE\s+DECLARANT)\b[^\n]{0,24}([A-Z][A-Z\s]{2,60})",
            declarant_block,
            re.IGNORECASE,
        )
        if m_nom_decl:
            candidate = re.sub(r"\s+", " ", m_nom_decl.group(1)).strip(" -|:;,.")
            if _is_plausible_declarant_name(candidate):
                fields["declarant_nom"] = candidate
                fields["declarant"] = candidate
                fields["nom_declarant"] = candidate
    if not fields.get("declarant_nom") and guided_declarant.get("declarant_nom"):
        fields["declarant_nom"] = guided_declarant["declarant_nom"]
        fields["declarant"] = guided_declarant["declarant"]
        fields["nom_declarant"] = guided_declarant["nom_declarant"]

    for country_field in (
        "pays_provenance",
        "pays_achat",
        "pays_premiere_destination",
        "pays_destination_finale",
    ):
        country = _country_cell_value(raw.get(country_field))
        if country:
            fields[country_field] = country
            if country_field == "pays_destination_finale":
                fields["pays_destination"] = country
    # Guided labeled extraction overrides noisy generic country reads.
    for key in ("pays_provenance", "pays_achat", "pays_premiere_destination", "pays_destination_finale", "pays_destination"):
        if guided_countries.get(key):
            fields[key] = guided_countries[key]

    for field, bounds in (
        ("bureau_frontiere", (1, 99)),
        ("destination", (1, 999)),
        ("poids_brut", (1, 99999)),
        ("poids_net", (1, 99999)),
        ("qualite_fiscale", (1, 99)),
        ("code_regime_financier", (10, 99)),
        ("code_delai", (10, 99)),
    ):
        number = _numeric_cell_value(
            raw.get(field),
            min_value=bounds[0],
            max_value=bounds[1],
            reject_cases=field not in {"bureau_frontiere", "destination", "code_regime_financier", "code_delai"},
            prefer_last=True,
        )
        if number:
            fields[field] = number

    # Rescue logistics row: Bureau frontiere / Destination / Localisation.
    if not fields.get("bureau_frontiere"):
        m_bf = re.search(r"\b(?:BUREAU\s+FRONTIERE|FRONTIERE)\b[^\d]{0,20}(\d{1,3})\b", text, re.IGNORECASE)
        if m_bf:
            fields["bureau_frontiere"] = m_bf.group(1)
    if not fields.get("destination"):
        m_dest = re.search(r"\bDESTINATION\b[^\d]{0,20}(\d{1,4})\b", text, re.IGNORECASE)
        if m_dest:
            fields["destination"] = m_dest.group(1)
    if not fields.get("localisation_export"):
        m_loc = re.search(r"\bLOCALISATION\b[^A-Z]{0,20}(EXPORT|IMPORT|TRANSIT)\b", text, re.IGNORECASE)
        if m_loc:
            fields["localisation_export"] = m_loc.group(1).upper()
    for key in ("bureau_frontiere", "destination", "localisation_export"):
        if not fields.get(key) and guided_logistics.get(key):
            fields[key] = guided_logistics[key]
    titre_code = _numeric_cell_value(
        raw.get("code_titre_ce_cell"),
        min_value=1,
        max_value=999,
        prefer_last=True,
    )
    if titre_code:
        fields["code_titre_ce"] = titre_code
    raw_nt = raw.get("numero_titre_ce_cell") or ""
    m_nt = re.search(r"\b(\d{5,12})\b", re.sub(r"\s+", "", str(raw_nt)))
    if m_nt:
        fields["numero_titre_ce"] = m_nt.group(1)
    if fields.get("destination") and str(fields.get("destination")).isdigit():
        if int(str(fields["destination"])) < 10:
            fields.pop("destination", None)

    transport = text.replace("™", "T")
    bt_raw = raw.get("block_transport") or ""
    bt = bt_raw.upper()
    # Bloc international en tête : évite d'associer le CAMION du transport national à l'international.
    bt_head = bt[:600]

    if re.search(r"\*{0,3}\s*AVION\s*\*{0,3}|\bAVION\b|\bAERIEN\b", bt_head, re.IGNORECASE):
        fields["mode_transport"] = "AVION"
        fields["transport_international_identite"] = "***AVION***" if "*" in (raw.get("block_transport") or "") else "AVION"
        fields["transport_international_mode"] = "7 - ROUTIER"
    elif re.search(r"\b(?:NAVIRE|BATEAU|VESSEL)\b", bt_head, re.IGNORECASE):
        fields["mode_transport"] = "NAVIRE"
        fields["transport_international_identite"] = "NAVIRE"
        fields["transport_international_mode"] = "7 - MARITIME"
    elif re.search(r"\bVOL\s+DU\b", bt_head, re.IGNORECASE):
        fields["mode_transport"] = "VOL DU"
        fields["transport_international_identite"] = "VOL DU"
        fields["transport_international_mode"] = "2 - AERIEN"
    elif re.search(r"\bCAMION\b", bt_head, re.IGNORECASE):
        fields["mode_transport"] = "CAMION"
        fields["transport_international_identite"] = "CAMION"
        fields["transport_international_mode"] = "4 - ROUTIER"
    elif re.search(r"\b(?:NAVIRE|BATEAU|VESSEL)\b", transport, re.IGNORECASE):
        fields["mode_transport"] = "NAVIRE"
        fields["transport_international_identite"] = "NAVIRE"
        fields["transport_international_mode"] = "7 - MARITIME"
    elif re.search(r"\bVOL\s+DU\b", transport, re.IGNORECASE):
        fields["mode_transport"] = "VOL DU"
        fields["transport_international_identite"] = "VOL DU"
        fields["transport_international_mode"] = "2 - AERIEN"
    elif re.search(r"\b(?:AVION|AERIEN)\b", transport, re.IGNORECASE):
        fields["mode_transport"] = "AVION"
        fields["transport_international_identite"] = "AVION"
        fields["transport_international_mode"] = "7 - ROUTIER"
    elif re.search(r"\bCAMION\b", transport, re.IGNORECASE):
        fields["mode_transport"] = "CAMION"
        fields["transport_international_identite"] = "CAMION"
        fields["transport_international_mode"] = "4 - ROUTIER"

    arrival = re.search(r"\b(\d{2}[\/\-.]\d{2}[\/\-.]\d{4})\b", raw.get("block_transport", "") or "")
    if arrival:
        fields["date_arrivee_depart"] = arrival.group(1).replace("/", "-").replace(".", "-")
    if re.search(r"\bT?N\s+4\s+CAMION\b", transport, re.IGNORECASE):
        fields["transport_national_mode"] = "4 - ROUTIER"
    if re.search(r"\bTN\b", transport, re.IGNORECASE):
        fields.setdefault("transport_international_nationalite", "TN TUNISIE")
        fields.setdefault("transport_national_nationalite", "TN TUNISIE")

    conditions = raw.get("block_conditions", "") or ""
    mode = re.search(r"\bMODE\s+LIVRAISON\b[^\nA-Z]{0,20}(EXW|CFR|DAP|FOB|CIF|CIP|CPT|DDP|FCA|FAS|DAT)\b", conditions, re.IGNORECASE)
    if not mode:
        mode = re.search(r"\b(EXW|CFR|DAP|FOB|CIF|CIP|CPT|DDP|FCA|FAS|DAT)\b", conditions, re.IGNORECASE)
    if mode:
        fields["mode_livraison"] = mode.group(1).upper()

    condition_row = re.search(
        r"\b(?:EXW|CFR|DAP|FOB|CIF|CIP|CPT|DDP|FCA|FAS|DAT)\b"
        r"[^\n\d]{0,30}(\d{1,2})(?![\/\-.])"
        r"[^\n\d]{1,30}(\d{1,2})(?![\/\-.])",
        conditions,
        re.IGNORECASE,
    )
    if condition_row:
        fields["mode_paiement"] = condition_row.group(1)
        fields["relation_acheteur_vendeur"] = condition_row.group(2)
        fields["engag_c"] = condition_row.group(2)

    finance = raw.get("block_finances", "") or ""
    conversion = re.search(r"\b(\d{1,2}[,.]\d{6,8})\s+(\d{4,12})\s*[,.]\s*(\d{3})\b", finance)
    if conversion:
        fields["taux_conversion"] = conversion.group(1).replace(",", ".")
        total = f"{conversion.group(2)}.{conversion.group(3)}"
        fields["valeur_fob_dt"] = total
        fields["valeur_dinars"] = total
        fields["valeur_totale"] = total

    amount = _first_amount(finance)
    if amount and "taux_conversion" not in fields:
        fields["taux_conversion"] = amount
    conversion_zone = re.search(r"\b(\d{1,2}[,.]\d{4,8})\b", finance)
    if conversion_zone:
        fields["cours_conversion_zone"] = conversion_zone.group(1).replace(",", ".")
    solde_match = re.search(
        r"\bSOLDE\s+AUTRES\s+[EÉ]L[ÉE]MENTS\s*[-+]?\s*PTFN\b[^\d]{0,20}(\d{1,12}(?:[.,]\d{1,3})?)",
        finance,
        re.IGNORECASE,
    )
    if solde_match:
        fields["solde_autres_elements_ptfn"] = solde_match.group(1).replace(",", ".")

    liquidation = raw.get("block_liquidation", "") or ""
    gdt = re.search(r"\b(602)\s+(\d{1,12}[,.]\d{3})\b", liquidation)
    if gdt:
        fields["code_gdt"] = gdt.group(1)
        fields["montant_liquidation"] = gdt.group(2).replace(",", ".")

    bureau = re.search(r"\b(\d{1,3})\s+BR\s*-\s*(ARIANA|TUNIS|SFAX|BIZERTE)\b", liquidation, re.IGNORECASE)
    if bureau:
        fields["code_bureau"] = bureau.group(1)
        fields["bureau_douane"] = f"BR - {bureau.group(2).upper()}"
        fields["designation_bureau"] = fields["bureau_douane"]

    route_tokens = {"SFAX", "RADES", "TUNIS", "TC"}
    for left, right in re.findall(r"\b([A-Z]{2,12})\s*-\s*([A-Z]{2,12})\b", liquidation, re.IGNORECASE):
        candidate = f"{left.upper()}-{right.upper()}"
        candidate = candidate.replace("SFAY", "SFAX")
        if candidate in {"BR-ARIANA", "BR-TUNIS", "BR-SFAX", "BR-BIZERTE"}:
            continue
        if any(token in candidate for token in route_tokens):
            fields["itineraire"] = candidate
            break

    if not fields.get("poids_brut") or not fields.get("poids_net"):
        m = re.search(
            r"POIDS\s+BRUT[^\d]{0,30}(\d{1,5})[^\n]{0,80}?POIDS\s+NET[^\d]{0,30}(\d{1,5})",
            text.upper(),
            re.IGNORECASE,
        )
        if m:
            brut = _valid_weight_token(m.group(1))
            net = _valid_weight_token(m.group(2))
            if brut:
                fields.setdefault("poids_brut", brut)
            if net:
                fields.setdefault("poids_net", net)

    # Additional rescue when OCR swaps order around article numeric columns.
    if not fields.get("poids_brut") or not fields.get("poids_net"):
        m_w = re.search(r"\bPOIDS\s+BRUT[^\d]{0,40}(\d{1,4})\b", text, re.IGNORECASE)
        n_w = re.search(r"\bPOIDS\s+NET[^\d]{0,40}(\d{1,4})\b", text, re.IGNORECASE)
        if m_w:
            brut = _valid_weight_token(m_w.group(1))
            if brut:
                fields.setdefault("poids_brut", brut)
        if n_w:
            net = _valid_weight_token(n_w.group(1))
            if net:
                fields.setdefault("poids_net", net)
    if not fields.get("poids_brut") and guided_article.get("poids_brut"):
        fields["poids_brut"] = guided_article["poids_brut"]
    if not fields.get("poids_net") and guided_article.get("poids_net"):
        fields["poids_net"] = guided_article["poids_net"]
    # Keep empty rather than copying potentially wrong value across gross/net.

    fob_cell = _amount_cell_value(raw.get("valeur_fob"))
    if fob_cell:
        fields["valeur_fob"] = fob_cell
        fields.setdefault("valeur_fob_dt", fob_cell)
    douane_cell = _amount_cell_value(raw.get("douane"))
    if douane_cell:
        fields["douane"] = douane_cell
        if not fields.get("valeur_dinars"):
            fields["valeur_dinars"] = douane_cell
    from app.services.parser_rules.article_value_fields import _extract_regime_from_source

    regime_ft = _extract_regime_from_source(text.upper())
    if regime_ft:
        fields["regime"] = regime_ft
    else:
        regime_cell = _numeric_cell_value(
            raw.get("regime"),
            min_value=10,
            max_value=99,
            reject_cases=False,
            prefer_last=True,
        )
        if regime_cell:
            fields["regime"] = regime_cell
    coef_cell = _amount_cell_value(raw.get("coefficient_ajustement"))
    if coef_cell:
        fields["coefficient_ajustement"] = coef_cell
    elif raw.get("coefficient_ajustement"):
        coef_num = _numeric_cell_value(
            raw.get("coefficient_ajustement"),
            min_value=0,
            max_value=999,
            reject_cases=False,
            prefer_last=True,
        )
        if coef_num:
            fields["coefficient_ajustement"] = coef_num

    m_fob_dou = re.search(
        r"\bFOB\b[^\d]{0,40}(\d{1,12}[.,]\d{3})\b[\s\S]{0,140}?\bDOUANE\b[^\d]{0,40}(\d{1,12}[.,]\d{3})\b",
        text,
        re.IGNORECASE,
    )
    if m_fob_dou:
        if not fields.get("valeur_fob"):
            fields["valeur_fob"] = m_fob_dou.group(1).replace(",", ".")
        if not fields.get("douane"):
            fields["douane"] = m_fob_dou.group(2).replace(",", ".")
        fields.setdefault("valeur_fob_dt", fields["valeur_fob"])
        fields.setdefault("valeur_dinars", fields.get("douane") or fields["valeur_fob"])

    if not fields.get("regime"):
        regime_ft2 = _extract_regime_from_source(text.upper())
        if regime_ft2:
            fields["regime"] = regime_ft2

    # Lot B: strict same-block recovery for regime codes from article table section.
    regime_block = " ".join(
        str(raw.get(k) or "")
        for k in ("block_article_1", "block_liquidation")
    )
    regime_triplet = _extract_regime_triplet_from_block(regime_block)
    for key, value in regime_triplet.items():
        if value and not fields.get(key):
            fields[key] = value

    agrement = re.search(r"\b(935)\s*[|:/\-]?\s*(\d{3,5})\b", liquidation)
    if agrement:
        fields["num_agrement"] = agrement.group(1)
        if not fields.get("num_repertoire"):
            fields["num_repertoire"] = agrement.group(2)

    auth = re.search(
        r"\b(D\d{2,6}[A-Z]{2,4}\d[A-Z])\b\s*[,/|]?\s*(\d{6,12})?",
        liquidation,
        re.IGNORECASE,
    )
    if auth:
        fields["cle_authentification"] = auth.group(1).upper()
        if auth.group(2):
            fields["qr_code"] = auth.group(2)

    for key in ("code_qcs", "qcs", "pfn", "numero_escale", "rubrique", "code_titre_ce", "numero_titre_ce"):
        if not fields.get(key) and guided_article.get(key):
            fields[key] = guided_article[key]

    eng_raw = raw.get("engagement_date") or raw.get("engagement") or ""
    m_eng_date = re.search(r"\b(\d{2}[-/.]\d{2}[-/.]\d{4})\b", str(eng_raw))
    if not m_eng_date:
        for pat in (
            r"\bECHEANCE\b[^\d]{0,30}(\d{2}[-/.]\d{2}[-/.]\d{4})",
            r"\bENGAGEMENT\b[^\d]{0,40}(\d{2}[-/.]\d{2}[-/.]\d{4})",
        ):
            m_eng_date = re.search(pat, text, re.IGNORECASE)
            if m_eng_date:
                break
    if m_eng_date:
        fields["engagement"] = m_eng_date.group(1).replace("/", "-").replace(".", "-")

    eng_roi = raw.get("texte_engagement_roi") or ""
    if eng_roi:
        m_roi = re.search(
            r"\b(?:JE\s+SOUSSIGN[ÉE]|SOUSSIGN[ÉE]|DECLAR[EÉ]\s+SOUS\s+LES\s+PEINES)\b[\s\S]{0,420}",
            eng_roi,
            re.IGNORECASE,
        )
        if m_roi:
            snippet = re.sub(r"\s+", " ", m_roi.group(0)).strip()
            if len(snippet) >= 12 and not fields.get("texte_engagement"):
                fields["texte_engagement"] = snippet[:300]

    cleaned_fields = {key: value for key, value in fields.items() if _clean_text(value)}
    if reject_reasons:
        cleaned_fields["field_reject_reasons"] = sorted(set(reject_reasons))
    return cleaned_fields


def _accept_dynamic_field(key, value):
    if not value:
        return None
    text = _clean_text(value)
    if not text:
        return None
    if key in {"importateur_nom", "importateur"}:
        return _clean_importer_name_cell(text)
    if key in {"declarant_nom", "declarant", "nom_declarant"}:
        return _clean_declarant_name_cell(text)
    if key in {"exportateur_nom", "exportateur"}:
        return _clean_exporter_name_cell(text)
    if key in {"pays_provenance", "pays_achat", "pays_premiere_destination", "pays_destination_finale", "pays_destination"}:
        return _country_cell_value(text)
    if key == "num_repertoire":
        return _extract_numeric_from_text(text, min_value=1000, max_value=99999)
    if key in {"nombre_colis", "nbre_articles", "nombre_articles"}:
        return _extract_numeric_from_text(text, min_value=1, max_value=999)
    if key in {"bureau_frontiere", "destination"}:
        return _extract_numeric_from_text(text, min_value=1, max_value=999)
    if key == "localisation_export":
        m_loc = re.search(r"\b(EXPORT|IMPORT|TRANSIT)\b", text, re.IGNORECASE)
        return m_loc.group(1).upper() if m_loc else None
    if key in {"poids_brut", "poids_net"}:
        return _extract_numeric_from_text(text, min_value=1, max_value=99999)
    if key in {"valeur_fob", "douane"}:
        return _amount_cell_value(text)
    if key == "regime":
        return _numeric_cell_value(text, min_value=1, max_value=99, reject_cases=False)
    if key == "coefficient_ajustement":
        return _amount_cell_value(text) or _numeric_cell_value(
            text, min_value=0, max_value=999, reject_cases=False
        )
    return text


def _extract_regime_triplet_from_block(value):
    if not value:
        return {}
    text = str(value).upper()
    out = {}
    m_fin = re.search(r"\b(?:REG(?:LEMENT)?\s*FINANCIER|FINANCIER)\b[^\d]{0,16}(\d{1,2})\b", text, re.IGNORECASE)
    m_del = re.search(r"\b(?:CODE\s+)?DELAI\b[^\d]{0,16}(\d{1,2})\b", text, re.IGNORECASE)
    m_oci = re.search(r"\b(?:CODE\s+)?OCI\b[^\d]{0,16}(\d{1,2})\b", text, re.IGNORECASE)
    if m_fin:
        out["code_regime_financier"] = m_fin.group(1)
    if m_del:
        out["code_delai"] = m_del.group(1)
    if m_oci:
        out["code_oci"] = m_oci.group(1)
    return out


def _is_plausible_declarant_name(value):
    if not value:
        return False
    text = re.sub(r"\s+", " ", str(value)).strip(" -|:;,.").upper()
    if len(text) < 4 or len(text) > 64:
        return False
    if DECLARANT_NOISE_TOKENS.search(text):
        return False
    if re.search(r"\b(?:SEKIT|EDDEYER|SFAX|TUNIS|RUE|AVENUE|SUITE)\b", text, re.IGNORECASE):
        return False
    return len(re.sub(r"[^A-Z]", "", text)) >= 5


def _valid_weight_token(token):
    if token is None:
        return None
    try:
        value = int(str(token))
    except Exception:
        return None
    if value < 1 or value > 99999:
        return None
    return str(value)


def _anchor_window(text, anchor_pattern, max_chars=180):
    if not text:
        return ""
    src = str(text)
    m = re.search(anchor_pattern, src, re.IGNORECASE)
    if not m:
        return ""
    start = m.end()
    return src[start : start + max_chars]


def _extract_near_anchor_numeric(text, anchor_pattern, min_digits=3, max_digits=10):
    window = _anchor_window(text, anchor_pattern, max_chars=120)
    if not window:
        return None
    m = re.search(rf"\b(\d{{{min_digits},{max_digits}}})\b", window)
    return m.group(1) if m else None


def _extract_guided_declarant_fields(text):
    if not text:
        return {}
    src = str(text).upper()
    out = {}
    # Pass 1: strict anchor-local extraction.
    rep_anchor = _extract_near_anchor_numeric(src, r"\bR[ÉE]PERTOI?RE\b", min_digits=3, max_digits=6)
    if rep_anchor:
        out["num_repertoire"] = rep_anchor
    credit_anchor = _extract_near_anchor_numeric(
        src,
        r"\b(?:N[°O]?\s*C[RE]DIT|NUM[EÉ]RO\s+C[RE]DIT|CREDIT)\b",
        min_digits=4,
        max_digits=10,
    )
    if credit_anchor:
        out["numero_credit"] = credit_anchor
    # Declarant name is usually between DECLARANT and MOYEN DE TRANSPORT blocks.
    m_decl_block = re.search(r"\bDECLARANT\b([\s\S]{0,220}?)(?:\bMOYEN\s+DE\s+TRANSPORT\b|$)", src, re.IGNORECASE)
    if m_decl_block:
        chunk = m_decl_block.group(1)
        inline = re.sub(r"\b(?:R[ÉE]PERTOI?RE|CREDIT|N[°O]|CODE)\b[\s\S]*$", "", chunk, flags=re.IGNORECASE)
        inline = re.sub(r"\bN\W*$", "", inline, flags=re.IGNORECASE)
        inline = re.sub(r"\s+", " ", inline).strip(" -|:;,.")
        if _is_plausible_declarant_name(inline):
            out["declarant_nom"] = inline
            out["declarant"] = inline
            out["nom_declarant"] = inline
            return out
        lines = [re.sub(r"\s+", " ", line).strip(" -|:;,.") for line in chunk.splitlines()]
        lines = [line for line in lines if line]
        for line in lines:
            if re.search(r"\b(?:R[ÉE]PERTOI?RE|CREDIT|N[°O]|CODE|TN|US|DE|FR)\b", line, re.IGNORECASE):
                continue
            if re.match(r"^\d{3,6}\b", line):
                continue
            if _is_plausible_declarant_name(line):
                out["declarant_nom"] = line
                out["declarant"] = line
                out["nom_declarant"] = line
                break

    # Pass 2: broader fallback patterns only when pass 1 missed values.
    if not out.get("num_repertoire"):
        m_rep = re.search(r"\bR[ÉE]PERTOI?RE\b[^\d]{0,24}(\d{3,6})\b", src, re.IGNORECASE)
        if m_rep:
            out["num_repertoire"] = m_rep.group(1)
    if not out.get("numero_credit"):
        m_credit = re.search(r"\b(?:N[°O]?\s*C[RE]DIT|NUM[EÉ]RO\s+C[RE]DIT|CREDIT)\b[^\d]{0,24}(\d{4,10})\b", src, re.IGNORECASE)
        if m_credit:
            out["numero_credit"] = m_credit.group(1)
    return out


def _extract_guided_logistics_fields(text):
    if not text:
        return {}
    src = str(text).upper()
    out = {}
    # Pass 1: strict same-row anchor extraction.
    m_row = re.search(
        r"\bBUREAU\s*FRONTI\w*\b[^\d]{0,20}(\d{1,3})[\s\S]{0,60}?\bDESTINATION\b[^\d]{0,20}(\d{1,4})[\s\S]{0,60}?\bLOCALIS\w*\b[^A-Z]{0,20}(EXPORT|IMPORT|TRANSIT)\b",
        src,
        re.IGNORECASE,
    )
    if m_row:
        out["bureau_frontiere"] = m_row.group(1)
        out["destination"] = m_row.group(2)
        out["localisation_export"] = m_row.group(3).upper()
        return out
    # Pass 2: independent anchor-local fallback.
    bf_anchor = _extract_near_anchor_numeric(src, r"\bBUREAU\s*FRONTI\w*\b", min_digits=1, max_digits=3)
    dst_anchor = _extract_near_anchor_numeric(src, r"\bDESTINATION\b", min_digits=1, max_digits=4)
    loc_window = _anchor_window(src, r"\bLOCALIS\w*\b", max_chars=60)
    m_loc_anchor = re.search(r"\b(EXPORT|IMPORT|TRANSIT)\b", loc_window, re.IGNORECASE) if loc_window else None
    m_bf = re.search(r"\bBUREAU\s*FRONTI\w*\b[^\d]{0,20}(\d{1,3})\b", src, re.IGNORECASE)
    m_dst = re.search(r"\bDESTINATION\b[^\d]{0,20}(\d{1,4})\b", src, re.IGNORECASE)
    m_loc = re.search(r"\bLOCALIS\w*\b[^A-Z]{0,20}(EXPORT|IMPORT|TRANSIT)\b", src, re.IGNORECASE)
    if bf_anchor:
        out["bureau_frontiere"] = bf_anchor
    if dst_anchor:
        out["destination"] = dst_anchor
    if m_loc_anchor:
        out["localisation_export"] = m_loc_anchor.group(1).upper()
    if m_bf:
        out.setdefault("bureau_frontiere", m_bf.group(1))
    if m_dst:
        out.setdefault("destination", m_dst.group(1))
    if m_loc:
        out.setdefault("localisation_export", m_loc.group(1).upper())
    return out


def _extract_guided_article_fields(text):
    if not text:
        return {}
    src = str(text).upper()
    out = {}
    m_q = re.search(
        r"\bCODE\s+QCS\b[^\d]{0,20}(\d{1,3})[\s\S]{0,40}?\bQCS\b[^\d]{0,20}(\d{1,5})[\s\S]{0,40}?\bPFN\b[^\d]{0,20}(\d{1,12}(?:[.,]\d{1,3})?)",
        src,
        re.IGNORECASE,
    )
    if m_q:
        out["code_qcs"] = m_q.group(1)
        out["qcs"] = m_q.group(2)
        out["pfn"] = m_q.group(3).replace(",", ".")
    m_w = re.search(r"\bPOIDS\s+BRUT(?:\s*\(KG\))?\b[^\d]{0,24}(\d{1,5})\b", src, re.IGNORECASE)
    m_n = re.search(r"\bPOIDS\s+NET(?:\s*\(KG\))?\b[^\d]{0,24}(\d{1,5})\b", src, re.IGNORECASE)
    if m_w:
        wv = _valid_weight_token(m_w.group(1))
        if wv:
            out["poids_brut"] = wv
    if m_n:
        nv = _valid_weight_token(m_n.group(1))
        if nv:
            out["poids_net"] = nv
    m_escale = re.search(r"N[°O]?\s*D[\'’]?\s*ESCALE[^\d]{0,12}(\d{3,6})", src, re.IGNORECASE)
    if m_escale:
        out["numero_escale"] = m_escale.group(1)
    m_rub = re.search(r"\bRUBRIQUE\b[^\d]{0,12}(\d{1,6})", src, re.IGNORECASE)
    if m_rub:
        out["rubrique"] = m_rub.group(1)
    m_ce = re.search(
        r"\bCODE\s+TITRE\s+CE[^\d]{0,50}(\d{1,3})[\s\S]{0,220}?\bNUM[ÉE]RO\s+TITRE\s+CE[^\d]{0,50}(\d{5,12})\b",
        src,
        re.IGNORECASE,
    )
    if m_ce:
        out["code_titre_ce"] = m_ce.group(1)
        out["numero_titre_ce"] = m_ce.group(2)
    else:
        tc, tn = extract_titre_ce_pair(text)
        if tc:
            out["code_titre_ce"] = tc
        if tn:
            out["numero_titre_ce"] = tn
    return out


def _extract_guided_country_fields(text):
    if not text:
        return {}
    src = str(text).upper()
    src = src.replace("U.S.A", "USA").replace("U S A", "USA")
    src = src.replace("1N", "TN").replace("TM", "TN")
    country_tokens = (
        r"(TN|US|FR|DE|IT|ES|BE|CY|CN|TR|NL|GB|PT)"
        r"|(?:TUNISIE|USA|FRANCE|ALLEMAGNE|ITALIE|ESPAGNE|BELGIQUE|CHYPRE|CHINE|TURQUIE|PAYS\s+BAS|ROYAUME\s+UNI|PORTUGAL)"
    )

    def _extract(label_pattern):
        m = re.search(
            rf"{label_pattern}[\s\S]{{0,120}}?\b({country_tokens})\b(?:[\s\S]{{0,24}}?\b({country_tokens})\b)?",
            src,
            re.IGNORECASE,
        )
        if not m:
            return None
        # Prefer first token unless it is a clear duplicate label fragment.
        t1 = m.group(1)
        t2 = m.group(2) if m.lastindex and m.lastindex >= 2 else None
        c1 = _country_cell_value(t1)
        c2 = _country_cell_value(t2) if t2 else None
        if c1 and c2:
            # Keep consistent CODE+LABEL pair if one is code and the other is same label.
            if c1.split(" ", 1)[0] == c2.split(" ", 1)[0]:
                return c1
        return c1 or c2

    out = {}
    out["pays_provenance"] = _extract(r"\bPAYS\s+DE\s+PROVENANCE\b")
    out["pays_achat"] = _extract(r"\bPAYS\s+D['’]?\s*ACHAT\b")
    out["pays_premiere_destination"] = _extract(r"\bPAYS\s+PREMIERE?\s+DESTINATION\b")
    out["pays_destination_finale"] = _extract(r"\bPAYS\s+DESTINATION\s+DEFINITIVE\b")
    # Cleanup None values
    out = {k: v for k, v in out.items() if v}
    if out.get("pays_provenance") and "ALLEMAGNE" in out["pays_provenance"].upper():
        prov = re.search(r"\bPAYS\s+DE\s+PROVENANCE\b([\s\S]{0,160})", src, re.IGNORECASE)
        if prov and re.search(r"\b(TN|TUNISIE)\b", prov.group(1), re.IGNORECASE):
            out["pays_provenance"] = "TN TUNISIE"
    if out.get("pays_provenance") and re.search(r"\b(CN|CHINE)\b", out["pays_provenance"].upper()):
        prov = re.search(r"\bPAYS\s+DE\s+PROVENANCE\b([\s\S]{0,220})", src, re.IGNORECASE)
        if prov and re.search(r"\b(TN|TUNISIE)\b", prov.group(1), re.IGNORECASE):
            out["pays_provenance"] = "TN TUNISIE"
    if out.get("pays_provenance") and re.search(r"^(US|FR)\s", out["pays_provenance"].upper()):
        prov = re.search(r"\bPAYS\s+DE\s+PROVENANCE\b([\s\S]{0,220})", src, re.IGNORECASE)
        if prov and re.search(r"\b(TN|TUNISIE)\b", prov.group(1), re.IGNORECASE):
            out["pays_provenance"] = "TN TUNISIE"
    if out.get("pays_achat") and re.search(r"^(US|FR)\s", out["pays_achat"].upper()):
        ach = re.search(r"\bPAYS\s+D['’]?\s*ACHAT\b([\s\S]{0,220})", src, re.IGNORECASE)
        if ach and re.search(r"\b(TN|TUNISIE)\b", ach.group(1), re.IGNORECASE):
            out["pays_achat"] = "TN TUNISIE"
    if not out.get("pays_achat") and out.get("pays_provenance"):
        ach = re.search(r"\bPAYS\s+D['’]?\s*ACHAT\b([\s\S]{0,220})", src, re.IGNORECASE)
        if ach and re.search(r"\b(TN|TUNISIE)\b", ach.group(1), re.IGNORECASE):
            out["pays_achat"] = "TN TUNISIE"
    if out.get("pays_premiere_destination") and "ALLEMAGNE" in out["pays_premiere_destination"].upper():
        prem = re.search(r"\bPAYS\s+PREMIERE?\s+DESTINATION\b([\s\S]{0,220})", src, re.IGNORECASE)
        if prem and re.search(r"\b(US|USA|U\.?\s*S\.?\s*A\.?)\b", prem.group(1), re.IGNORECASE):
            out["pays_premiere_destination"] = "US USA"
    if out.get("pays_destination_finale"):
        dest_chunk = re.search(r"\bPAYS\s+DESTINATION\s+DEFINITIVE\b([\s\S]{0,220})", src, re.IGNORECASE)
        if dest_chunk:
            chunk_u = dest_chunk.group(1).upper()
            cur_u = out["pays_destination_finale"].upper()
            if re.search(r"\b(PT|PORTUGAL)\b", chunk_u):
                out["pays_destination_finale"] = _country_cell_value("PT") or "PT PORTUGAL"
                out["pays_destination"] = out["pays_destination_finale"]
            elif re.search(r"\b(CY|CHYPRE)\b", chunk_u):
                out["pays_destination_finale"] = _country_cell_value("CY") or "CY CHYPRE"
                out["pays_destination"] = out["pays_destination_finale"]
            elif re.search(r"\b(FR|FRANCE)\b", chunk_u) and re.search(r"\b(DE|ALLEMAGNE)\b", cur_u):
                out["pays_destination_finale"] = "FR FRANCE"
                out["pays_destination"] = out["pays_destination_finale"]
    if out.get("pays_destination_finale"):
        out.setdefault("pays_destination", out["pays_destination_finale"])
    return out


def extract_template_fields(img, fast_mode=False, ocr_scale=2.0):
    """Extract high-value fixed cells from the customs declaration template."""
    if img is None or (hasattr(img, "size") and img.size == 0):
        return {}

    if settings.OCR_DEBUG_ZONES:
        h, w = img.shape[:2]
        logger.info("[OCR DEBUG] template_extractor start image_size=%sx%s", w, h)

    raw = {}
    header_cells = extract_header_cell_fields(img, fast_mode=fast_mode, ocr_scale=ocr_scale)
    if header_cells:
        raw.update(header_cells)
        if settings.OCR_DEBUG_ZONES:
            logger.info("[OCR DEBUG] header_cell_ocr fields=%s", list(header_cells.keys()))

    dynamic_fields, dynamic_metrics = extract_dynamic_fields(
        img,
        fast_mode=fast_mode,
        ocr_scale=ocr_scale,
    )
    scale = 1.5 if fast_mode else max(ocr_scale, 2.0)
    fixed_fallback_fields = []
    fixed_fallback_blocks = []
    field_confidences = {}
    for zone in FIELD_ZONES:
        # Lot 3: progressive suppression of fixed zones.
        # If dynamic already supplied a strict field, keep fixed zone only for debug block.
        if zone.name in dynamic_fields and not zone.name.startswith("block_"):
            box = _box_by_ratio(img, zone.ratio)
            details = _recognize_zone_with_roi_expand(
                img,
                zone.ratio,
                zone_psm=zone.psm,
                ocr_scale=scale,
                field_name=zone.name,
                critical=zone.name in STRICT_NUMERIC_ZONES
                or zone.name
                in {
                    "exportateur_nom",
                    "importateur_nom",
                    "declarant_nom",
                    "num_repertoire",
                    "texte_engagement_roi",
                },
                fast_mode=fast_mode,
            )
            text = details["text"]
            cleaned = _clean_text(text)
            if settings.OCR_DEBUG_ZONES:
                save_zone_crop(
                    img,
                    zone.name,
                    box,
                    tag="fixed_zone",
                    ocr_text=text,
                    confidence=float(details.get("confidence") or 0.0),
                    engine=str(details.get("engine") or ""),
                )
            if cleaned:
                raw[zone.name] = cleaned
                fixed_fallback_blocks.append(zone.name)
                field_confidences[zone.name] = {
                    "confidence": details["confidence"],
                    "engine": details["engine"],
                    "source": "fixed_block_only",
                }
                if settings.OCR_DEBUG_ZONES:
                    logger.info(
                        "[OCR DEBUG] fixed_block_only zone=%s box=%s psm=%s text='%s'",
                        zone.name,
                        box,
                        zone.psm,
                        cleaned[:140],
                    )
            continue

        box = _box_by_ratio(img, zone.ratio)
        details = _recognize_zone_with_roi_expand(
            img,
            zone.ratio,
            zone_psm=zone.psm,
            ocr_scale=scale,
            field_name=zone.name,
            critical=zone.name in STRICT_NUMERIC_ZONES
            or zone.name
            in {
                "exportateur_nom",
                "importateur_nom",
                "code_importateur",
                "declarant_nom",
                "num_repertoire",
                "texte_engagement_roi",
            },
            fast_mode=fast_mode,
        )
        text = details["text"]
        cleaned = _clean_text(text)
        if settings.OCR_DEBUG_ZONES:
            save_zone_crop(
                img,
                zone.name,
                box,
                tag="fixed_zone",
                ocr_text=text,
                confidence=float(details.get("confidence") or 0.0),
                engine=str(details.get("engine") or ""),
            )
        if cleaned:
            if zone.name not in raw or zone.name in STRICT_NUMERIC_ZONES:
                raw[zone.name] = cleaned
            fixed_fallback_fields.append(zone.name)
            field_confidences[zone.name] = {
                "confidence": details["confidence"],
                "engine": details["engine"],
                "source": "fixed_zone",
            }
            if settings.OCR_DEBUG_ZONES:
                logger.info(
                    "[OCR DEBUG] fixed_zone zone=%s box=%s psm=%s text='%s'",
                    zone.name,
                    box,
                    zone.psm,
                    cleaned[:140],
                )

    fields = _extract_direct_fields(raw)
    for key, value in dynamic_fields.items():
        if fields.get(key):
            continue
        accepted = _accept_dynamic_field(key, value)
        if accepted:
            fields[key] = accepted
            if settings.OCR_DEBUG_ZONES:
                logger.info("[OCR DEBUG] dynamic_field_applied field=%s value='%s'", key, str(accepted)[:140])

    if _ZONE_CONFLICTS:
        fields["zone_conflict_flags"] = [f"{a}<->{b}" for a, b in _ZONE_CONFLICTS]
    fallback_count = len(set(fixed_fallback_fields) - set(dynamic_fields.keys()))
    dynamic_count = len(dynamic_metrics.get("dynamic_fields", []))
    coverage = round(dynamic_count / max(1, len(FIELD_ZONES)), 4)
    fields["template_quality"] = {
        "strategy": "hybrid_dynamic_first",
        "dynamic_anchor_count": dynamic_metrics.get("anchor_count", 0),
        "dynamic_field_count": dynamic_count,
        "dynamic_coverage_ratio": coverage,
        "fixed_fallback_count": fallback_count,
    }
    if fixed_fallback_blocks:
        fields["fixed_fallback_blocks"] = sorted(set(fixed_fallback_blocks))
    if field_confidences:
        fields["template_field_confidences"] = field_confidences
    for name, value in raw.items():
        fields[f"block_{name}"] = value
    if settings.OCR_DEBUG_ZONES:
        logger.info(
            "[OCR DEBUG] template_extractor done dynamic=%s fixed_fallback=%s conflicts=%s",
            dynamic_count,
            fallback_count,
            len(_ZONE_CONFLICTS),
        )
    return fields
