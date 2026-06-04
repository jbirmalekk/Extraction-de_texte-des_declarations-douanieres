import re
import unicodedata
from datetime import datetime

from app.services.parser_rules.article_rules import extract_articles_from_text
from app.services.parser_rules.customs_fallbacks import apply_customs_template_fallbacks as _apply_customs_template_fallbacks
from app.services.parser_rules.customs_helpers import empty_result as _empty_result, extract_titre_ce_pair
from app.services.parser_rules.geo_constants import COUNTRY_BY_CODE, COUNTRY_NAME_TO_CODE
from app.services.parser_rules.ocr_noise import normalize_ocr_noise as _normalize_ocr_noise
from app.services.parser_rules.scoring_rules import validate_fields

TYPES_VALIDES = {"DAE", "EA", "SE", "EE", "DUM", "IM", "IM4", "IM6", "EX", "EX1", "EX3", "T1"}
DEVISES_VALIDES = {"USD", "EUR", "GBP", "TND", "CHF", "JPY", "CAD"}

TRANSPORT_MODE_CODE_MAP = {
    "1": "MARITIME",
    "2": "AERIEN",
    "3": "FERROVIAIRE",
    "4": "ROUTIER",
    "5": "ROUTIER",
    "6": "AERIEN",
    "7": "MARITIME",
}


def _normalize_country_token(value):
    if value is None:
        return ""
    token = re.sub(r"[\.|,/\\'’`-]+", " ", str(value).upper())
    token = re.sub(r"\s+", " ", token).strip()
    return token


def _country_display(value):
    token = _normalize_country_token(value)
    if not token:
        return None

    if token in COUNTRY_BY_CODE:
        return f"{token} - {COUNTRY_BY_CODE[token]}"

    code = COUNTRY_NAME_TO_CODE.get(token)
    if code:
        return f"{code} - {COUNTRY_BY_CODE[code]}"

    return token


def _mode_display(code, label=None):
    if code is None and label is None:
        return None
    code_text = str(code).strip() if code is not None else ""
    label_text = re.sub(r"\s+", " ", str(label).strip().upper()) if label is not None else ""
    if code_text and label_text:
        return f"{code_text} - {label_text}"
    return label_text or code_text


def _sanitize_company_name(value):
    if not value:
        return value

    candidate = re.sub(r"\s+", " ", str(value)).strip(" -|")

    focused = re.search(
        r"\b([A-Z][A-Z\s\.&\-]{3,90}\b(?:KG|SARL|SYSTEMS|ENGINEERING|PRECISION|INDUSTR\w*|TRADING))\b",
        candidate,
        re.IGNORECASE,
    )
    if focused:
        candidate = focused.group(1)

    candidate = re.sub(r"^(?:[A-Z]{1,3}\s+){1,4}", "", candidate)
    candidate = re.sub(r"\b(?:Gait|AiR|oye|to)\b", " ", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\s+", " ", candidate).strip(" -|")

    return candidate if len(re.sub(r"[^A-Za-z]", "", candidate)) >= 6 else value


def _safe_float(value):
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9.]", "", str(value).replace(",", ".").replace(" ", ""))
    try:
        return float(cleaned) if cleaned else None
    except Exception:
        return None


def _is_valid_date(value):
    if not value:
        return False
    try:
        datetime.strptime(str(value), "%d-%m-%Y")
        return True
    except Exception:
        return False


def _is_probable_code(value, min_len=3, max_len=12):
    if value is None:
        return False
    token = re.sub(r"\s+", "", str(value).upper())
    if not token:
        return False
    if len(token) < min_len or len(token) > max_len:
        return False
    if not re.fullmatch(r"[A-Z0-9]+", token):
        return False
    if token in COUNTRY_BY_CODE:
        return False
    if token in COUNTRY_NAME_TO_CODE:
        return False
    if token.isalpha() and len(token) > 3:
        return False
    return any(ch.isdigit() for ch in token)


def _normalize_transport_token(value):
    """Normalize transport mode/identity tokens (strip trailing 'DU', map variants).

    Examples:
    - 'BATEAU DU' -> 'BATEAU'
    - 'VOL DU' -> 'VOL'
    - '1 - MARITIME' -> 'MARITIME'
    """
    if not value:
        return None
    t = re.sub(r"\s+", " ", str(value).upper()).strip()
    # remove trailing punctuation
    t = re.sub(r"[\.,;:]$", "", t)
    # remove trailing ' DU' or ' DU.' etc
    t = re.sub(r"\s+DU\b\.?", "", t)
    # if expression contains a hyphen like '1 - MARITIME', take the right side
    if "-" in t:
        parts = [p.strip() for p in t.split("-") if p.strip()]
        if len(parts) >= 2:
            t = parts[-1]
    # Map common tokens to a canonical form
    if re.search(r"\bNAVIRE\b|\bVESSEL\b", t):
        return "NAVIRE"
    if re.search(r"\bBATEAU\b", t):
        return "BATEAU"
    if re.search(r"\bMARITIME\b", t):
        return "MARITIME"
    if re.search(r"\bVOL\b|\bAVION\b", t):
        return "AVION"
    if re.search(r"\bCAMION\b|\bROUTIER\b", t):
        return "CAMION"
    if re.search(r"\bTRAIN\b|\bFERROVIAIRE\b", t):
        return "TRAIN"
    # Fallback: return the cleaned token
    return t.strip() or None


def _extract_articles_from_text(text):
    return extract_articles_from_text(text)


def valider_champs(data):
    return validate_fields(data, types_valides=TYPES_VALIDES, devises_valides=DEVISES_VALIDES)


def _legacy_parse_fields(text, zones_text=None, article_rows=None):
    raw = _normalize_ocr_noise(text or "")
    source_zones = zones_text or {}
    zones = {
        name: _normalize_ocr_noise(content)
        for name, content in source_zones.items()
    }

    z_header = zones.get("header", raw)
    z_header_right = zones.get("header_right", raw)
    z_pays = zones.get("pays", raw)
    z_fob_zone = zones.get("fob_zone", raw)
    z_exportateur = zones.get("exportateur", raw)
    z_importateur = zones.get("importateur", raw)
    z_declarant = zones.get("declarant", raw)
    z_transport = zones.get("transport", raw)
    z_conditions = zones.get("conditions", raw)
    z_finances = zones.get("finances", raw)
    z_marchandises = zones.get("marchandises", raw)
    z_taxes = zones.get("taxes", raw)
    z_liquidation = zones.get("liquidation", raw)
    z_final = zones.get("final", raw)

    data = {
        "exportateur": None,
        "adresse_exportateur": None,
        "code_exportateur": None,
        "importateur": None,
        "adresse_importateur": None,
        "code_importateur": None,
        "declarant": None,
        "repertoire": None,
        "numero_credit": None,
        "numero_declaration": None,
        "date_declaration": None,
        "numero_dae": None,
        "type_declaration": None,
        "nbre_articles": None,
        "nombre_articles": None,
        "nombre_colis": None,
        "exportateur_nom": None,
        "exportateur_code": None,
        "importateur_nom": None,
        "importateur_pays": None,
        "declarant_code": None,
        "declarant_nom": None,
        "transport_international_nationalite": None,
        "transport_international_mode": None,
        "transport_international_identite": None,
        "transport_national_nationalite": None,
        "transport_national_mode": None,
        "mode_transport": None,
        "date_arrivee_depart": None,
        "pays_provenance": None,
        "pays_achat": None,
        "pays_premiere_destination": None,
        "pays_destination": None,
        "pays_destination_finale": None,
        "adresse_entreposage": None,
        "mode_livraison": None,
        "mode_paiement": None,
        "relation_acheteur_vendeur": None,
        "engagement": None,
        "devise": None,
        "valeur_totale": None,
        "assurance": None,
        "fret": None,
        "montant_ptfn": None,
        "valeur_dinars": None,
        "valeur_fob_dt": None,
        "taux_conversion": None,
        "designation_marchandises": None,
        "numero_article": None,
        "code_sh_ndp": None,
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
        "code_titre_ce": None,
        "numero_titre_ce": None,
        "code_regime_precedent": None,
        "code_regime_financier": None,
        "code_delai": None,
        "code_oci": None,
        "douane": None,
        "valeur_fob": None,
        "regime": None,
        "coefficient_ajustement": None,
        "description_marchandise": None,
        "bureau_frontiere": None,
        "destination": None,
        "localisation_export": None,
        "taxes": [],
        "articles": article_rows or _extract_articles_from_text(raw),
        "bureau_douane": None,
        "code_bureau": None,
        "designation_bureau": None,
        "code_taxe": None,
        "assiette": None,
        "quotite": None,
        "montant": None,
        "code_gdt": None,
        "montant_total": None,
        "total": None,
        "totaux": None,
        "montant_liquidation": None,
        "itineraire": None,
        "commissaire_douane": None,
        "num_agrement": None,
        "num_repertoire": None,
        "texte_engagement": None,
        "nom_declarant": None,
        "date_validation": None,
        "cachet": None,
        "cle_authentification": None,
        "qr_code": None,
        "score_confiance": None,
        "qualite": None,
        "flags_validation": [],
    }

    def s3(pattern, primary, secondary=None, flags=0):
        for source in (primary, secondary, raw):
            if not source:
                continue
            match = re.search(pattern, source, flags)
            if match:
                return match
        return None

    def set_if_empty(key, value):
        if value is None:
            return
        if not data.get(key):
            data[key] = value

    def norm_amount(value):
        if value is None:
            return None
        return str(value).replace(",", ".").strip()

    # Exportateur block
    exportateur_block = ""
    exportateur_block_match = re.search(
        r"Exportateur[\s\S]{0,600}?(?=Importateur|D[eé]clarant|Pays\s+de\s+provenance|$)",
        raw, re.IGNORECASE,
    )
    if exportateur_block_match:
        exportateur_block = exportateur_block_match.group(0)
    
    # Pattern 1 : format "5751:NOM"
    match = s3(r"(?:\d{4}:)([A-Z][A-Z\s\.\&]{5,120})", z_exportateur, exportateur_block or raw, re.IGNORECASE)
    if match:
        nom_raw = match.group(1)
        # Garder jusqu'au saut de ligne OU jusqu'à un mot-clé de rupture
        nom_clean = re.split(
            r"\r?\n|Declaration|Certificat|Code\s+[A-Z]|Num[eé]ro|Date\s+\d",
            nom_raw, maxsplit=1
        )[0].strip()
        data["exportateur_nom"] = re.sub(r"\s+", " ", nom_clean)
    
    # Pattern 2 : si pas trouvé, chercher ligne après "Exportateur"
    if not data.get("exportateur_nom"):
        lines = exportateur_block.splitlines() if exportateur_block else raw.splitlines()
        capture_next = False
        collected = []
        for line in lines:
            line_clean = line.strip()
            if re.search(r"\bexportateur\b", line_clean, re.IGNORECASE):
                capture_next = True
                continue
            if capture_next:
                if not line_clean or re.search(
                    r"\b(importateur|d[eé]clarant|code|num[eé]ro|date|pays)\b",
                    line_clean, re.IGNORECASE
                ):
                    break
                if len(re.sub(r"[^A-Za-z]", "", line_clean)) >= 4:
                    collected.append(line_clean)
                if len(collected) >= 3:   # max 3 lignes pour le nom
                    break
        if collected:
            data["exportateur_nom"] = " ".join(collected).strip()
        
        # Header
        match = s3(r"(?:Num[eé]ro|رقم)[^\d]{0,20}(\d{6})\b", z_header, None, re.IGNORECASE)
        if not match:
            # Fallback : premier 6 chiffres isolés dans le header
            match = s3(r"\b(\d{6})\b", z_header)
        if match:
            data["numero_declaration"] = match.group(1)
    
        # FOB : chercher d'abord dans z_fob_zone
        for src in [z_fob_zone, z_finances, raw]:
            if not src:
                continue
            m = re.search(
                r"(?:valeur\s+douane|FOB|valeur\s+en\s+dinars)[^\d]{0,30}(\d{4,12}[\.,]\d{3})",
                src, re.IGNORECASE
            )
            if m:
                data["valeur_fob_dt"] = m.group(1).replace(",", ".")
                break
    
        # Date déclaration : chercher d'abord avec contexte "Numéro/Date"
        m_date_decl = s3(
            r"(?:D[eé]claration|Num[eé]ro)[^\n]{0,60}?(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})", z_header, None, re.IGNORECASE)
        if m_date_decl:
            data["date_declaration"] = m_date_decl.group(1)
    
        # Date arrivée/départ : chercher avec contexte "arrivée" ou "départ"
        m_date_arr = s3(
            r"(?:arriv[eé]e?|d[eé]part|Date\s+arriv)[^\n]{0,30}?(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})", raw, None, re.IGNORECASE)
        if m_date_arr:
            data["date_arrivee_depart"] = m_date_arr.group(1)
    
        # Fallback : toutes les dates dans l'ordre
        if not data.get("date_declaration") or not data.get("date_arrivee_depart"):
            all_dates = re.findall(r"\b(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})\b", raw)
            if all_dates and not data.get("date_declaration"):
                data["date_declaration"] = all_dates[0]
            if len(all_dates) >= 2 and not data.get("date_arrivee_depart"):
                data["date_arrivee_depart"] = all_dates[1]
    
        if data.get("date_declaration") and not _is_valid_date(str(data["date_declaration"]).replace("/", "-").replace(".", "-")):
            all_dates = [d.replace("/", "-").replace(".", "-") for d in re.findall(r"\b(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})\b", raw)]
            valid_dates = [date_value for date_value in all_dates if _is_valid_date(date_value)]
            if valid_dates:
                data["date_declaration"] = valid_dates[0]
    
        if data.get("date_arrivee_depart") and not _is_valid_date(str(data["date_arrivee_depart"]).replace("/", "-").replace(".", "-")):
            all_dates = [d.replace("/", "-").replace(".", "-") for d in re.findall(r"\b(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})\b", raw)]
            valid_dates = [date_value for date_value in all_dates if _is_valid_date(date_value)]
            if len(valid_dates) >= 2:
                data["date_arrivee_depart"] = valid_dates[1]
            elif valid_dates:
                data["date_arrivee_depart"] = valid_dates[0]
    
        match = s3(r"\b(D\.?A\.?E\.?|E\.?A\.?|S\.?E\.?|D\.?U\.?M\.?|IM\s?\d{1,3}|EX\s?\d{1,3})\b", z_header, None, re.IGNORECASE)
        if match:
            data["type_declaration"] = re.sub(r"\.", "", match.group(1)).strip().upper()
    
        match = s3(r"nbre\s+tot[^\d]{0,15}(\d{1,3})", z_header, None, re.IGNORECASE)
        if not match:
            match = s3(r"\bEA\s+(\d{1,3})\b", z_header)
        if match:
            data["nbre_articles"] = match.group(1)
    
        match = s3(r"\b(?:N(?:bre|ore)?\s*total\s*articles?|articles?\s*total(?:es)?)\b[^\d]{0,20}(\d{1,3})", raw, None, re.IGNORECASE)
        if match:
            set_if_empty("nombre_articles", match.group(1))
    
        # REMPLACER le bloc nbre_colis par :
    
        # Nbre total colis : plusieurs patterns
        colis_match = s3(
            r"(?:nbre\s+total\s+colis|nombre\s+de\s+colis|n\.?\s*colis)[^\d]{0,15}(\d{1,4})",
            z_header, raw, re.IGNORECASE
        )
        if not colis_match:
            # Dans le header : "18" après "Nbre coils" ou "Nbre colis"
            colis_match = s3(
                r"Nbre\s+coli[s|h][^\d]{0,10}(\d{1,4})",
                raw, None, re.IGNORECASE
            )
        if not colis_match:
            # Chercher "Nbre colis" + espace + nombre dans header_right
            colis_match = s3(
                r"\bNbre\b[^\n]{0,40}(\d{1,4})\s*$",
                z_header, None, re.IGNORECASE | re.MULTILINE
            )
        if colis_match:
            data["nombre_colis"] = colis_match.group(1)
            
        match = s3(r"\b(?:r[eé]pertoire)\b[^\d]{0,20}(\d{1,6})", z_declarant, None, re.IGNORECASE)
        if match:
            set_if_empty("repertoire", match.group(1))
    
        match = s3(r"\b(?:n[°o]?\s*cr[eé]dit|num[eé]ro\s+cr[eé]dit)\b[^\d]{0,20}(\d{1,10})", raw, None, re.IGNORECASE)
        if match:
            set_if_empty("numero_credit", match.group(1))
    
        # Exportateur
        match = s3(r"(?:\d{4}:)([A-Z][A-Z\s\.\&]{5,120})", z_exportateur, exportateur_block or raw, re.IGNORECASE)
        if match:
            exportateur_nom = re.split(
                r"\r?\n|Dectaration|Declaration|Certificat|Code|Num[eé]ro|Date|Pays",
                match.group(1),
                maxsplit=1,
            )[0].strip()
            data["exportateur_nom"] = re.sub(r"\s+", " ", exportateur_nom)
        if not data.get("exportateur_nom"):
            match = s3(r"Exportate\w*[\s\S]{0,180}?\n\s*([A-Z][A-Z0-9\s\.\&\-]{8,90})", exportateur_block or raw, None, re.IGNORECASE)
            if match:
                candidate = re.sub(r"\s+", " ", match.group(1)).strip(" -|")
                alpha_len = len(re.sub(r"[^A-Za-z]", "", candidate))
                if (
                    alpha_len >= 12
                    and not re.search(r"\b(Num[eé]ro|Date|Code|D[eé]claration|Importateur|TTN)\b", candidate, re.IGNORECASE)
                    and len([token for token in candidate.split() if len(token) >= 4]) >= 2
                ):
                    data["exportateur_nom"] = candidate
    
        if not data.get("exportateur_nom"):
            match = s3(r"\b([A-Z][A-Z\s\.&\-]{10,90}\b(?:ENGINEERING|PRECISION|MACHIN\w*|INDUSTR\w*|SYSTEMS))\b", exportateur_block or raw, None, re.IGNORECASE)
            if match:
                data["exportateur_nom"] = re.sub(r"\s+", " ", match.group(1)).strip()
    
        if not data.get("adresse_exportateur") and exportateur_block:
            address_candidates = re.findall(
                r"\b\d{2,4}\s+[A-Z][A-Z]{3,}(?:\s+[A-Z][A-Z]{3,}){1,}\b",
                exportateur_block,
                re.IGNORECASE,
            )
            if address_candidates:
                candidate = max(address_candidates, key=len)
                candidate = re.sub(r"\s+", " ", candidate).strip(" -|")
                if len(re.sub(r"[^A-Za-z]", "", candidate)) >= 8:
                    data["adresse_exportateur"] = candidate
    
        if not data.get("adresse_exportateur") and exportateur_block:
            for line in exportateur_block.splitlines():
                cleaned_line = re.sub(r"[|]+", " ", re.sub(r"\s+", " ", line)).strip(" -|")
                candidate_match = re.search(
                    r"\b(\d{2,4}\s+[A-Z][A-Z]{2,}(?:\s+[A-Z][A-Z]{2,}){1,})\b",
                    cleaned_line,
                    re.IGNORECASE,
                )
                if candidate_match:
                    candidate = re.sub(r"\s+", " ", candidate_match.group(1)).strip(" -|")
                    if len(re.sub(r"[^A-Za-z]", "", candidate)) >= 8:
                        data["adresse_exportateur"] = candidate
                        break
    
        if data.get("exportateur_nom"):
            cleaned_exportateur = re.sub(
                r"^(?:[A-Z]{1,4}\s+){0,4}(?:DATE|NUM(?:[EÉ]RO)?)\s+",
                "",
                str(data["exportateur_nom"]),
                flags=re.IGNORECASE,
            )
            cleaned_exportateur = re.sub(r"^(?:[A-Z]{1,2}\s+)+", "", cleaned_exportateur)
            data["exportateur_nom"] = re.sub(r"\s+", " ", cleaned_exportateur).strip()
        match = s3(r"\b(\d{6,8}[A-Z])\b", z_exportateur, None, re.IGNORECASE)
        if match:
            data["exportateur_code"] = match.group(1).upper()
    
    # ── Bloc importateur 
    importateur_block = ""
    imp_block_match = re.search(
        r"Importateur[\s\S]{0,500}?(?=D[eé]clarant|Pays\s+de\s+provenance|Moyen\s+de\s+transport|$)",
        raw, re.IGNORECASE,
    )
    if imp_block_match:
        importateur_block = imp_block_match.group(0)
    
    # Nom importateur : CL + chiffres (avec espace optionnel)
    match = s3(
        r"(CL\s?\d{3,6}\s+[A-Z][A-Z0-9\s\.\&\-]{5,80})",
        z_importateur, importateur_block, re.IGNORECASE
    )
    if match:
        nom_raw = match.group(1).strip()
        nom_clean = re.split(r"\n|\bCode\b|\bAdresse\b|\bPays\b|\bR[eé]pertoire\b",
                             nom_raw, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        data["importateur_nom"] = re.sub(r"\s+", " ", nom_clean)
    
    # Si toujours pas trouvé (pas de code CL)
    if not data.get("importateur_nom"):
        match = s3(
            r"Importateur[^\n]{0,20}\n\s*([A-Z][A-Z0-9\s\.\&\-]{8,80})",
            importateur_block, raw, re.IGNORECASE
        )
        if match:
            candidate = re.sub(r"\s+", " ", match.group(1)).strip()
            if len(re.sub(r"[^A-Za-z]", "", candidate)) >= 8:
                data["importateur_nom"] = candidate
    
    # Code importateur : afficher UNIQUEMENT si "CL" suivi de chiffres est clairement présent
    # Ne pas afficher si c'est ambigu
    cl_match = re.search(r"\b(CL\s?\d{3,6})\b", importateur_block or z_importateur, re.IGNORECASE)
    if cl_match:
        data["code_importateur"] = re.sub(r"\s", "", cl_match.group(1)).upper()
    else:
        data["code_importateur"] = None   # ← FORCER None si pas trouvé
    
    # Adresse importateur : la ligne qui SUIT le nom de l'importateur
    # (pas avant, pas confondue avec CL...)
    if data.get("importateur_nom"):
        # Chercher l'adresse après le nom dans le bloc
        nom_escaped = re.escape(data["importateur_nom"][:20])
        adr_match = re.search(
            nom_escaped + r"[\s\S]{0,10}\n\s*([A-Z0-9][^\n]{8,100})",
            importateur_block or raw, re.IGNORECASE
        )
        if not adr_match:
            # Fallback : chercher "EMP SEKIET" ou autre adresse connue
            adr_match = re.search(
                r"(EMP\s+[A-Z][^\n]{5,80}|RTE\s+[A-Z][^\n]{5,80}|\d+\s+[A-Z][^\n]{5,80})",
                importateur_block or raw, re.IGNORECASE
            )
        if adr_match:
            adr = re.sub(r"\s+", " ", adr_match.group(1)).strip()
            # Rejeter si ça ressemble à un nom d'entreprise
            if not re.search(r"\b(GMBH|KG|SARL|SA\b|SYSTEMS|ENGINEERING)\b",
                             adr, re.IGNORECASE):
                data["adresse_importateur"] = adr
                           
        match = s3(r"Pays\s+d['’]?achat[^\n]{0,40}(TN|DE|FR|IT|ES|BE|US|CN|TR|NL|GB)\b", raw, None, re.IGNORECASE)
        if match:
            data["pays_achat"] = _country_display(match.group(1))
        match = s3(r"\b(U\.?S\.?A\.?|ALLEMAGNE|FRANCE|ITALIE|ESPAGNE|CHINE|TURQUIE|BELGIQUE|PAYS\s+BAS|ROYAUME\s+UNI|TUNISIE)\b", z_importateur, None, re.IGNORECASE)
        if match:
            data["importateur_pays"] = _country_display(match.group(1))
        # L'adresse d'entreposage est dans la case 9 — a droite du header
        # Format: "EMP SEKIET EDDAYER RTE DE MAHDIA KM10 SFAX"
        entreposage_match = re.search(
            r"Adresse\s+des\s+lieux\s+d[\W_]*entreposage"
            r"[\s\S]{0,30}\n\s*([A-Z0-9][^\n]{8,120})",
            raw, re.IGNORECASE
        )
        if entreposage_match:
            adr = re.sub(r"\s+", " ", entreposage_match.group(1)).strip()
            # Valider que ca ressemble a une adresse (pas un nom d'entreprise seul)
            if re.search(r"\b(RTE|KM|SFAX|TUNIS|ARIANA|SUITE|EMP|AVENUE|RUE|ZONE)\b",
                         adr, re.IGNORECASE):
                data["adresse_entreposage"] = adr
    
        if not data.get("adresse_entreposage"):
            # Chercher pattern "EMP..." ou "SUITE SA..." connus
            known_adr = re.search(
                r"((?:EMP|SUITE\s+SA|ZONE\s+IND)\s+[A-Z][^\n]{10,100})",
                raw, re.IGNORECASE
            )
            if known_adr:
                data["adresse_entreposage"] = re.sub(r"\s+", " ", known_adr.group(1)).strip()
    
        # Declarant
        match = s3(r"d[eé]clarant[^\n]{0,15}(\d{4})\b", z_declarant, None, re.IGNORECASE)
        if match:
            data["declarant_code"] = match.group(1)
        match = re.search(r"(STE\s+SMART\s+CUSTOMS[A-Z\s]{0,20})", raw, re.IGNORECASE)
        if match:
            data["declarant_nom"] = re.split(r"\s+(?:PS|Pays|Go|pres|BR)", match.group(1))[0].strip()
        if not data.get("declarant_nom"):
            match = s3(r"(STE\s+SMART\s+CUST\w*\s+BROK\w*[A-Z\s]{0,30})", raw, None, re.IGNORECASE)
            if match:
                data["declarant_nom"] = re.sub(r"\s+", " ", match.group(1)).strip()
       
        # Répertoire : nombre après "Répertoire" dans la zone déclarant
        rep_match = s3(
            r"R[eé]pertoire[^\d]{0,20}(\d{3,6})",
            z_declarant, None, re.IGNORECASE
        )
        if rep_match:
            data["repertoire"] = rep_match.group(1)
        else:
            data["repertoire"] = None
    
        # ────────────────────────────────────────────
        # TRANSPORT INTERNATIONAL (vers l'etranger)
        # ────────────────────────────────────────────
        # Pattern visuel de la declaration :
        # Nationalite | Mode | Identite          | Date arrivee/depart
        # TN          | 7    | BATEAU DU         | 30-08-2025
    
        transport_intl_match = re.search(
            r"(?:vers\s+l.?[eé]tranger|moyen\s+de\s+transport)"
            r"[\s\S]{0,200}?"
            r"(TN|DE|FR|IT|ES|BE|US|CN|TR|NL|GB)\s+"
            r"(\d{1,2})\s+"
            r"(BATEAU\s+DU|VOL\s+DU|CAMION|AVION(?:\s+DU)?|IT\s*\d{2,4}|[A-Z\s]{4,30}?)"
            r"[\s\S]{0,80}?"
            r"(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})",
            z_transport or raw, re.IGNORECASE
        )
    
        if transport_intl_match:
            country_code = transport_intl_match.group(1).upper()
            mode_code = transport_intl_match.group(2)
            identite = re.sub(r"\s+", " ", transport_intl_match.group(3)).strip().upper()
            date_dep = transport_intl_match.group(4)
    
            data["transport_international_nationalite"] = COUNTRY_BY_CODE.get(country_code, country_code)
            data["transport_international_mode"] = TRANSPORT_MODE_CODE_MAP.get(mode_code, mode_code)
            data["transport_international_identite"] = identite
            data["mode_transport"] = identite
            data["date_arrivee_depart"] = date_dep
        else:
            # Fallback 1 : chercher BATEAU DU / VOL DU / AVION directement
            ident_match = re.search(
                r"\b(BATEAU\s+DU|VOL\s+DU|AVION\s+DU|CAMION|IT\s?\d{2,4})\b",
                raw, re.IGNORECASE
            )
            if ident_match:
                identite = ident_match.group(1).strip().upper()
                data["transport_international_identite"] = identite
                data["mode_transport"] = identite
    
            # Fallback 2 : date arrivee contextuelle
            date_arr_match = re.search(
                r"(?:Date\s+arriv[eé]e?[\/\s]?d[eé]part|arriv[eé]e?\/d[eé]part)"
                r"[^\d]{0,20}(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})",
                raw, re.IGNORECASE
            )
            if date_arr_match:
                data["date_arrivee_depart"] = date_arr_match.group(1)
    
        # ────────────────────────────────────────────
        # TRANSPORT NATIONAL (transit/cabotage)
        # ────────────────────────────────────────────
        transport_natl_match = re.search(
            r"(?:transit[\/\s]?cabotage|transport.*?national)"
            r"[\s\S]{0,150}?"
            r"(TN|DE|FR|IT|ES|BE|US|CN|TR|NL|GB)\s+"
            r"(\d{1,2})\s+"
            r"(CAMION|TRAIN|ROUTIER|FERRY|[A-Z\s]{4,20}?)"
            r"(?:\s|$)",
            raw, re.IGNORECASE
        )
    
        if transport_natl_match:
            country_code = transport_natl_match.group(1).upper()
            mode_code = transport_natl_match.group(2)
            identite_nat = re.sub(r"\s+", " ", transport_natl_match.group(3)).strip().upper()
    
            data["transport_national_nationalite"] = COUNTRY_BY_CODE.get(country_code, country_code)
            data["transport_national_mode"] = TRANSPORT_MODE_CODE_MAP.get(mode_code, identite_nat)
        else:
            # Fallback : CAMION est le plus courant
            cam = re.search(r"\bCAMION\b", raw, re.IGNORECASE)
            if cam and not data.get("transport_national_mode"):
                data["transport_national_mode"] = "CAMION"
                data["transport_national_nationalite"] = data.get("transport_international_nationalite", "TUNISIE")
    
        # ────────────────────────────────────────────
        # BUREAU / DESTINATION / LOCALISATION
        # ────────────────────────────────────────────
        bureau_dest_match = re.search(
            r"(?:Bureau\s*Fronti[eè]re?|Fronti[eè]re?)"
            r"[^\d]{0,20}(\d{1,3})"
            r"[\s\S]{0,80}?Destination[^\d]{0,20}(\d{1,4})"
            r"[\s\S]{0,80}?Localisation[^\w]{0,20}(EXPORT|IMPORT|TRANSIT)",
            raw, re.IGNORECASE
        )
        if bureau_dest_match:
            data["bureau_frontiere"] = bureau_dest_match.group(1)
            data["destination"] = bureau_dest_match.group(2)
            data["localisation_export"] = bureau_dest_match.group(3).upper()
        else:
            # Fallback separe
            bf = re.search(r"Fronti[eè]re?[^\d]{0,15}(\d{1,3})", raw, re.IGNORECASE)
            if bf:
                data["bureau_frontiere"] = bf.group(1)
            dest = re.search(r"\bDestination\b[^\d]{0,15}(\d{1,4})", raw, re.IGNORECASE)
            if dest:
                data["destination"] = dest.group(1)
            loc = re.search(r"\b(EXPORT|IMPORT|TRANSIT)\b", raw)
            if loc:
                data["localisation_export"] = loc.group(1).upper()
    
        def _format_pays(code, nom):
            """Retourne le pays au format 'TN TUNISIE' comme dans le document."""
            code = (code or "").strip().upper()
            nom = (nom or "").strip().upper()
            if code and nom:
                return f"{code} {nom}"
            if code:
                return f"{code} {COUNTRY_BY_CODE.get(code, code)}"
            return nom
    
        # Pattern generique pour lire les cases pays
        # Format dans le doc : [TN] [TUNISIE] sur la meme ligne
        pays_pattern = r"(TN|DE|FR|US|IT|ES|BE|CN|TR|NL|GB)\s+(TUNISIE|FRANCE|ALLEMAGNE|U\.?S\.?A\.?|ITALIE|ESPAGNE|BELGIQUE|CHINE|TURQUIE|PAYS\s+BAS|ROYAUME\s+UNI|U\.S\.A)"
    
        # Pays de provenance (case 11 gauche)
        prov_match = re.search(
            r"Pays\s+de\s+provenance[\s\S]{0,120}?" + pays_pattern,
            raw, re.IGNORECASE
        )
        if prov_match:
            data["pays_provenance"] = _format_pays(prov_match.group(1), prov_match.group(2))
        else:
            # Fallback code seul
            prov_code = re.search(r"provenance[\s\S]{0,60}?(TN|DE|FR|US|IT|ES)", raw, re.IGNORECASE)
            if prov_code:
                code = prov_code.group(1).upper()
                data["pays_provenance"] = f"{code} {COUNTRY_BY_CODE.get(code, code)}"
    
        # Pays d'achat (case 12 droite)
        achat_match = re.search(
            r"Pays\s+d[\W_]*achat[\s\S]{0,120}?" + pays_pattern,
            raw, re.IGNORECASE
        )
        if achat_match:
            data["pays_achat"] = _format_pays(achat_match.group(1), achat_match.group(2))
        else:
            # Souvent identique a pays_provenance
            data["pays_achat"] = data.get("pays_provenance")
    
        # Pays de premiere destination (case 13)
        prem_dest_match = re.search(
            r"premi[eè]re?\s+destination[\s\S]{0,120}?" + pays_pattern,
            raw, re.IGNORECASE
        )
        if prem_dest_match:
            data["pays_premiere_destination"] = _format_pays(
                prem_dest_match.group(1), prem_dest_match.group(2)
            )
    
        # Pays de destination definitive (case 14)
        def_dest_match = re.search(
            r"destination\s+d[eé]finitive[\s\S]{0,120}?" + pays_pattern,
            raw, re.IGNORECASE
        )
        if def_dest_match:
            data["pays_destination_finale"] = _format_pays(
                def_dest_match.group(1), def_dest_match.group(2)
            )
            data["pays_destination"] = data["pays_destination_finale"]
        else:
            # Fallback : 2eme pays different du pays de provenance
            all_pays = re.findall(pays_pattern, raw, re.IGNORECASE)
            if len(all_pays) >= 2:
                # Prendre le premier pays different du pays de provenance
                prov_code = (data.get("pays_provenance") or "")[:2]
                for code, nom in all_pays:
                    if code.upper() != prov_code.upper():
                        data["pays_destination_finale"] = _format_pays(code, nom)
                        data["pays_destination"] = _format_pays(code, nom)
                        break
    
        # Finances
        for source in (z_finances, raw):
            if not source:
                continue
            match1 = re.search(r"\d{2}[-\/]\d{2}[-\/]\d{4}[^\n]{0,40}(USD|EUR|GBP|TND|CHF)[^\n\d]{0,5}(\d{3,10}[.,]\d{3})", source)
            match2 = re.search(r"\b(USD|USP|USO|U5D|EUR|GBP|TND|CHF)\b[^\n\d]{0,10}(\d{3,10}[.,]\d{3})", source, re.IGNORECASE)
            match3 = re.search(r"(?:PTFN|PTEN|PIFN)[^\n]{0,100}(\d{4,10}[.,]\d{3})", source, re.IGNORECASE)
            if match1:
                data["devise"] = match1.group(1).upper()
                data["montant_ptfn"] = match1.group(2).replace(",", ".")
                break
            if match2:
                data["devise"] = match2.group(1).upper().replace("USP", "USD").replace("USO", "USD").replace("U5D", "USD")
                data["montant_ptfn"] = match2.group(2).replace(",", ".")
                break
            if match3:
                data["montant_ptfn"] = match3.group(1).replace(",", ".")
    
        amount_candidates = []
        for source in (z_finances, raw):
            if not source:
                continue
            amount_candidates.extend(re.findall(
                r"(?:valeur\s+douane\s+totale|valeur\s+en\s+dinars|fob|facturation|dinars)[^\d]{0,40}(\d{2,12}(?:[.,]\d{3,4})?)",
                source,
                re.IGNORECASE,
            ))
        if amount_candidates:
            best_amount = max(amount_candidates, key=lambda candidate: _safe_float(candidate) or -1)
            normalized_amount = best_amount.replace(",", ".")
            set_if_empty("valeur_fob_dt", normalized_amount)
            set_if_empty("valeur_dinars", normalized_amount)
    
        match = s3(r"\b(\d{1,2}[.,]\d{6,8})\b", z_finances)
        if match:
            data["taux_conversion"] = match.group(1).replace(",", ".")
    
        montant_ptfn_value = _safe_float(data.get("montant_ptfn"))
        taux_conversion_value = _safe_float(data.get("taux_conversion"))
        if montant_ptfn_value is not None and taux_conversion_value is not None:
            converted_amount = f"{montant_ptfn_value * taux_conversion_value:.3f}"
            set_if_empty("valeur_fob_dt", converted_amount)
            set_if_empty("valeur_dinars", converted_amount)
    
        match = s3(r"\b(EXW|CFR|DAP|FOB|CIF|CIP|CPT|DDP|FCA|FAS|DAT)\b", z_conditions, raw)
        if match:
            data["mode_livraison"] = match.group(1).upper()
    
        # Mode de paiement (case 17)
        paiement_match = re.search(
            r"Mode\s+(?:de\s+)?paiement[^\n:]{0,20}[:\-]?\s*([^\n]{2,40})",
            raw, re.IGNORECASE
        )
        if paiement_match:
            val = paiement_match.group(1).strip()
            # Accepter les codes courants : 1, 2, 30J, VIREMENT, etc.
            if re.search(r"\b(\d{1,2}|VIREMENT|CREDIT|AVANCE|30\s*J|60\s*J|90\s*J)\b",
                         val, re.IGNORECASE):
                data["mode_paiement"] = val
            elif len(val) <= 20:
                data["mode_paiement"] = val
    
        # Relation acheteur/vendeur (case 18)
        relation_match = re.search(
            r"Relat\.?\s*(?:Ach\.?\s*Vend\.?|acheteur[\/\s]vendeur)[^\n:]{0,20}[:\-]?\s*([^\n]{1,30})",
            raw, re.IGNORECASE
        )
        if relation_match:
            val = relation_match.group(1).strip()
            if val and len(val) <= 20:
                data["relation_acheteur_vendeur"] = val
    
        # Engagement (case 19 / texte en bas du document)
        engagement_match = re.search(
            r"Engag\.?\s*C?\.?[^\n:]{0,20}[:\-]?\s*([^\n]{2,60})",
            raw, re.IGNORECASE
        )
        if not engagement_match:
            engagement_match = re.search(
                r"(?:Engagement|Engag\b)[^\n]{0,30}\n\s*([A-Z][^\n]{5,200})",
                raw, re.IGNORECASE
            )
        if engagement_match:
            val = re.sub(r"\s+", " ", engagement_match.group(1)).strip()
            if 5 <= len(val) <= 200:
                data["engagement"] = val
    
        # Texte engagement (en bas, paragraphe A/B/C...)
        texte_eng_match = re.search(
            r"(?:A\s+Je\s+soussign[eé]|Je\s+d[eé]clare\s+sous|soussign[eé]\s+d[eé]clare)"
            r"[\s\S]{0,300}?(?=B\s+Je|C\s+Je|$)",
            raw, re.IGNORECASE
        )
        if texte_eng_match:
            val = re.sub(r"\s+", " ", texte_eng_match.group(0)).strip()
            if len(val) >= 20:
                data["texte_engagement"] = val[:300]
    
        match = s3(r"valeur\s+totale[^\d]{0,20}(\d{1,12}(?:[.,]\d{1,3})?)", raw, None, re.IGNORECASE)
        if match:
            set_if_empty("valeur_totale", match.group(1).replace(",", "."))
    
        # Assurance : chercher uniquement si precede du mot "Assurance" ET suivi d'un nombre
        assurance_match = re.search(
            r"\bAssurance\b[^\d\n]{0,20}(\d{1,12}(?:[.,]\d{1,3})?)",
            raw, re.IGNORECASE
        )
        if assurance_match:
            val = _safe_float(assurance_match.group(1))
            # Mettre None si la valeur est 0 (champ vide dans le doc)
            if val and val > 0:
                data["assurance"] = assurance_match.group(1).replace(",", ".")
            else:
                data["assurance"] = None
        else:
            data["assurance"] = None
    
        # Fret : idem
        fret_match = re.search(
            r"\bFret\b[^\d\n]{0,20}(\d{1,12}(?:[.,]\d{1,3})?)",
            raw, re.IGNORECASE
        )
        if fret_match:
            val = _safe_float(fret_match.group(1))
            if val and val > 0:
                data["fret"] = fret_match.group(1).replace(",", ".")
            else:
                data["fret"] = None
        else:
            data["fret"] = None
    
        match = s3(r"valeur\s+en\s+dinars[^\d]{0,20}(\d{2,12}(?:[.,]\d{3,4})?)", raw, None, re.IGNORECASE)
        if match:
            set_if_empty("valeur_dinars", match.group(1).replace(",", "."))
    
        match = s3(r"valeur\s+douane\s+totale[^\d]{0,30}(\d{2,12}(?:[.,]\d{3,4})?)", raw, None, re.IGNORECASE)
        if match:
            amount = norm_amount(match.group(1))
            set_if_empty("valeur_dinars", amount)
            set_if_empty("valeur_totale", amount)
    
        if not data.get("valeur_totale") and data.get("valeur_dinars"):
            data["valeur_totale"] = data["valeur_dinars"]
    
        # Marchandises
        match = s3(r"d[eé]signation\s+des\s+marchandises[^\n]{0,30}\n([^\n]{5,100})", z_marchandises, None, re.IGNORECASE)
        if match:
            data["designation_marchandises"] = re.sub(r"^[\|\s\W]{0,5}", "", match.group(1)).strip()
        if not data.get("designation_marchandises"):
            match = s3(r"Autres\s+parties\s+d(?:['’\s]?|\s+)avions?", raw, None, re.IGNORECASE)
            if match:
                data["designation_marchandises"] = re.sub(r"\s+", " ", match.group(0)).strip()
        match = s3(r"Poids\s+brut[^\d\n]{0,40}(\d{2,6})", z_marchandises, None, re.IGNORECASE)
        if match:
            data["poids_brut"] = match.group(1)
        match = s3(r"Poids\s+net[^\d\n]{0,40}(\d{2,6})", z_marchandises, None, re.IGNORECASE)
        if match:
            data["poids_net"] = match.group(1)
    
        if not data.get("poids_brut") or not data.get("poids_net"):
            match = s3(
                r"Poid[s5]\s*brut[^\d]{0,30}(\d{1,4})[^\n\d]{0,40}Poid[s5]\s*net[^\d]{0,30}(\d{1,4})",
                raw,
                None,
                re.IGNORECASE,
            )
            if match:
                set_if_empty("poids_brut", match.group(1))
                set_if_empty("poids_net", match.group(2))
    
        match = s3(r"Article\s*n[°o]?[^^\d]{0,20}(\d{1,3})\s+(\d{8,12})\s+(TN|DE|FR|IT|ES|BE|US|CN|TR|NL|GB)\s+(\d{1,12}(?:[.,]\d{1,3})?)", raw, None, re.IGNORECASE)
        if match:
            set_if_empty("numero_article", match.group(1))
            set_if_empty("code_sh_ndp", match.group(2))
            set_if_empty("code_pays_origine", match.group(3).upper())
            set_if_empty("valeur_prise_en_charge", norm_amount(match.group(4)))
    
        if not data.get("code_sh_ndp") or not data.get("code_pays_origine"):
            match = s3(r"\b(\d{8,12})\s+(TN|DE|FR|IT|ES|BE|US|CN|TR|NL|GB)\s+(\d{1,12}(?:[.,]\d{3,4})?)\b", raw, None, re.IGNORECASE)
            if match:
                set_if_empty("code_sh_ndp", match.group(1))
                set_if_empty("code_pays_origine", match.group(2).upper())
                set_if_empty("valeur_prise_en_charge", norm_amount(match.group(3)))
    
            match = s3(r"\b(\d{1,3})\s+(\d{8,12})\s+(TN|DE|FR|IT|ES|BE|US|CN|TR|NL|GB)\s+(\d{1,12}(?:[.,]\d{3,4})?)\b", raw, None, re.IGNORECASE)
            if match:
                set_if_empty("numero_article", match.group(1))
                set_if_empty("code_sh_ndp", match.group(2))
                set_if_empty("code_pays_origine", match.group(3).upper())
                set_if_empty("valeur_prise_en_charge", norm_amount(match.group(4)))
    
        match = s3(r"\bCode\s+QCS\b[\s\S]{0,120}?(\d{1,3})\s+(\d{1,4})\s+(\d{1,12}(?:[.,]\d{3,4})?)", raw, None, re.IGNORECASE)
        if match:
            set_if_empty("code_qcs", match.group(1))
            set_if_empty("qcs", match.group(2))
            pfn_cell = match.group(3).replace(",", ".")
            set_if_empty("pfn", pfn_cell)

        match = s3(r"\b(?:Code\s*)?(?:QCS|OCS|ACS)\b[\s\S]{0,120}?(\d{1,3})\s+(\d{1,4})\s+(\d{1,12}(?:[.,]\d{3,4})?)", raw, None, re.IGNORECASE)
        if match:
            set_if_empty("code_qcs", match.group(1))
            set_if_empty("qcs", match.group(2))
            pfn_cell = match.group(3).replace(",", ".")
            set_if_empty("pfn", pfn_cell)

        if not data.get("code_qcs") or not data.get("pfn"):
            match = s3(r"\b(\d{1,3})\s+(\d{1,4})\s+(\d{1,12}(?:[.,]\d{3,4})?)\b", raw, None, re.IGNORECASE)
            if match and data.get("code_sh_ndp") and data.get("code_pays_origine"):
                set_if_empty("code_qcs", match.group(1))
                set_if_empty("qcs", match.group(2))
                g3_raw = match.group(3)
                if re.search(r"[.,]\d{3}", g3_raw):
                    set_if_empty("pfn", g3_raw.replace(",", "."))
                else:
                    set_if_empty("valeur_prise_en_charge", norm_amount(g3_raw))
    
        match = s3(r"imposition\s+sp[ée]ciale[\s\S]{0,80}?(\d{2,4})\s+(\d{2,4})", raw, None, re.IGNORECASE)
        if match:
            set_if_empty("imposition_speciale", match.group(1))
            set_if_empty("code_regime_precedent", match.group(2))
    
        # Regimes douaniers: declare / transit / precedent
        regime_triplet_match = s3(
            r"r[ée]gimes?\s+douaniers[\s\S]{0,80}?d[ée]clar[ée][^\d]{0,12}(\d{2,4})(?:[\s\S]{0,50}?transit[^\d]{0,12}(\d{2,4}))?[\s\S]{0,80}?pr[ée]c[ée]dent[^\d]{0,12}(\d{2,4})",
            raw,
            None,
            re.IGNORECASE,
        )
        if regime_triplet_match:
            set_if_empty("regime_douanier", regime_triplet_match.group(1))
            if regime_triplet_match.group(2):
                set_if_empty("code_regime_financier", regime_triplet_match.group(2))
            set_if_empty("code_regime_precedent", regime_triplet_match.group(3))
    
        match = s3(r"r[eé]gimes?\s+douaniers?[^\d]{0,20}(\d{2,4})", raw, None, re.IGNORECASE)
        if match:
            set_if_empty("regime_douanier", match.group(1))
    
        match = s3(r"reglement\s+financier[^\d]{0,20}(\d{2,4})", raw, None, re.IGNORECASE)
        if match:
            set_if_empty("code_regime_financier", match.group(1))
    
        match = s3(
            r"CODE\s+TITRE\s+CE[^\d]{0,50}(\d{1,3})[\s\S]{0,220}?NUM[ÉE]RO\s+TITRE\s+CE[^\d]{0,50}(\d{5,12})",
            raw,
            None,
            re.IGNORECASE,
        )
        if match:
            set_if_empty("code_titre_ce", match.group(1))
            set_if_empty("numero_titre_ce", match.group(2))

        if not data.get("code_titre_ce") or not data.get("numero_titre_ce"):
            tc, tn = extract_titre_ce_pair(raw)
            set_if_empty("code_titre_ce", tc)
            set_if_empty("numero_titre_ce", tn)
    
        origin_country = COUNTRY_BY_CODE.get(str(data.get("code_pays_origine") or "").upper())
        if origin_country:
            data["pays_provenance"] = origin_country
            data["transport_international_nationalite"] = origin_country
            data["transport_national_nationalite"] = origin_country
    
        # Taxes
        for source in (z_taxes, raw):
            if not source:
                continue
            found = re.findall(r"\b(\d{3})\s+(\d{1,10}[.,]\d{3})\s+(\d{1,6}[.,]\d{6})\s+(\d{1,10}[.,]\d{3})", source)
            if found:
                data["taxes"] = [
                    {"code": row[0], "assiette": row[1].replace(",", "."), "quotite": row[2].replace(",", "."), "montant": row[3].replace(",", ".")}
                    for row in found
                ]
                break
    
        if data["taxes"]:
            first_tax = data["taxes"][0]
            set_if_empty("code_taxe", first_tax.get("code"))
            set_if_empty("assiette", first_tax.get("assiette"))
            set_if_empty("quotite", first_tax.get("quotite"))
            set_if_empty("montant", first_tax.get("montant"))
    
        # Liquidation
        match = s3(r"\bBR\s*-\s*(ARIANA|TUNIS|SFAX|BIZERTE)\b", z_liquidation, None, re.IGNORECASE)
        if match:
            city = match.group(1).upper().strip()
            data["bureau_douane"] = f"BR - {city}"
            set_if_empty("code_bureau", city)
        else:
            match = s3(r"\bbureau[^\n]{0,40}(ARIANA|TUNIS|SFAX|BIZERTE)\b", z_liquidation, None, re.IGNORECASE)
            if match:
                city = match.group(1).upper().strip()
                data["bureau_douane"] = f"BR - {city}"
                set_if_empty("code_bureau", city)
    
        liquidation_amount_candidates = []
        for source in (z_liquidation, raw):
            if not source:
                continue
            liquidation_amount_candidates.extend(
                re.findall(r"\b(?:Total|Totaux)\b[^\d]{0,12}(\d{1,12}(?:[.,]\d{3,4})?)", source, re.IGNORECASE)
            )
            liquidation_amount_candidates.extend(
                re.findall(r"\bTot\b[^\d]{0,12}\[?(\d{1,12}(?:[.,]\d{3,4})?)", source, re.IGNORECASE)
            )
            liquidation_amount_candidates.extend(
                re.findall(r"\bmontant\s+liquidation\b[^\d]{0,12}(\d{1,12}(?:[.,]\d{3,4})?)", source, re.IGNORECASE)
            )
        if liquidation_amount_candidates:
            best_liquidation_amount = max(
                liquidation_amount_candidates,
                key=lambda candidate: _safe_float(candidate) or -1,
            )
            data["montant_liquidation"] = best_liquidation_amount.replace(",", ".")
    
        match = s3(
            r"Code\s+GDT[^\d]{0,12}(\d{1,3})[\s\S]{0,120}?BR\s*-\s*(?:ARIANA|TUNIS|SFAX|BIZERTE)",
            z_liquidation,
            raw,
            re.IGNORECASE,
        )
        if match:
            data["code_gdt"] = match.group(1)
        else:
            match = s3(r"(?:GDT|Code\s+GDT)[^\d]{0,10}(\d{1,3})", z_liquidation, None, re.IGNORECASE)
            if match:
                data["code_gdt"] = match.group(1)
    
        if data.get("bureau_douane"):
            city = str(data["bureau_douane"]).replace("BR -", "").strip().upper()
            row_code_match = s3(rf"\b(\d{{1,2}})\s+BR\s*-\s*{city}\b", z_liquidation, raw, re.IGNORECASE)
            if row_code_match and (not data.get("code_gdt") or str(data.get("code_gdt")) in {"0", "602"}):
                data["code_gdt"] = row_code_match.group(1)
    
        match = s3(r"\bN\s*[°o]?\s*d[\'’]?escale\b[^\d]{0,20}(\d{1,6})", z_liquidation, None, re.IGNORECASE)
        if match:
            set_if_empty("bureau_frontiere", match.group(1))
    
        match = s3(r"\bLocalisation\b[^A-Z0-9]{0,20}([A-Z]{3,20})\b", z_liquidation, None, re.IGNORECASE)
        if match:
            set_if_empty("localisation_export", match.group(1).upper())
    
        match = s3(r"\bDestination\b[^A-Z0-9]{0,20}([A-Z]{2,20}|\d{1,4})\b", z_liquidation, None, re.IGNORECASE)
        if match:
            set_if_empty("destination", match.group(1).upper())
    
        structured_row_match = s3(
            r"Fronti\w*[\s\S]{0,80}?Destination[\s\S]{0,80}?Localisation[\s\S]{0,120}?(\d{1,3})\s+(\d{1,4})\s+(EXPORT|IMPORT|TRANSIT)",
            raw,
            None,
            re.IGNORECASE,
        )
        if structured_row_match:
            set_if_empty("bureau_frontiere", structured_row_match.group(1))
            set_if_empty("destination", structured_row_match.group(2))
            set_if_empty("localisation_export", structured_row_match.group(3).upper())
    
        if not data.get("bureau_frontiere") or not data.get("destination") or not data.get("localisation_export"):
            loose_structured_match = s3(
                r"Fronti\w*[\s\S]{0,220}?(\d{1,3})\s+(\d{1,4})\s+(EXPORT|IMPORT|TRANSIT)\b",
                raw,
                None,
                re.IGNORECASE,
            )
            if loose_structured_match:
                set_if_empty("bureau_frontiere", loose_structured_match.group(1))
                set_if_empty("destination", loose_structured_match.group(2))
                set_if_empty("localisation_export", loose_structured_match.group(3).upper())
    
        if not data.get("bureau_frontiere") or not data.get("destination") or not data.get("localisation_export"):
            match = s3(r"\n\s*(\d{1,3})\s+(\d{1,4})\s+([A-Z]{3,20})\b", raw, None, re.IGNORECASE)
            if match:
                location_token = match.group(3).upper()
                if location_token in {"EXPORT", "IMPORT", "TRANSIT"}:
                    set_if_empty("bureau_frontiere", match.group(1))
                    set_if_empty("destination", match.group(2))
                    set_if_empty("localisation_export", location_token)
    
        # Final
        match = s3(r"\b([A-Z]{2,6}[\-][A-Z]{2,6})\b", z_final)
        if match:
            data["itineraire"] = match.group(1)
    
        if not data.get("itineraire"):
            match = s3(r"\b([A-Z]{2,12}\s*-\s*[A-Z]{2,12})\b", z_liquidation, raw, re.IGNORECASE)
            if match:
                data["itineraire"] = re.sub(r"\s+", "", match.group(1).upper().replace("-", " - ")).replace("  ", " ").strip()
    
        itinerary_candidates = re.findall(r"\b([A-Z]{2,12}\s*-\s*[A-Z]{2,12})\b", raw.upper())
        itinerary_candidates = [
            candidate.strip()
            for candidate in itinerary_candidates
            if "BR -" not in candidate and "LOCALISATION" not in candidate and "FRET" not in candidate
        ]
        if itinerary_candidates:
            def _itinerary_score(candidate):
                score = 0
                if any(token in candidate for token in ("SFAX", "RADES", "TC", "TUNIS", "ARIANA", "BIZERTE")):
                    score += 2
                if len(candidate.replace(" ", "")) <= 16:
                    score += 1
                return score
    
            best_itinerary = max(itinerary_candidates, key=_itinerary_score)
            if _itinerary_score(best_itinerary) > 0:
                data["itineraire"] = re.sub(r"\s*\-\s*", " - ", best_itinerary).strip()
    
        match = s3(r"935\s*[|/:\-]?\s*(\d{2,5})", z_final, raw, re.IGNORECASE)
        if match:
            data["num_agrement"] = "935"
            data["num_repertoire"] = match.group(1)
    
        match = s3(r"N\s*[°o]?\s*agrement\]?[^\d]{0,20}(\d{2,6})", z_final, None, re.IGNORECASE)
        if match:
            set_if_empty("num_agrement", match.group(1))
    
        match = s3(r"N\s*[°o]?\s*repertoire\]?[^\d]{0,20}(\d{2,6})", z_final, None, re.IGNORECASE)
        if match:
            set_if_empty("num_repertoire", match.group(1))
    
        if not data.get("num_agrement") or not data.get("num_repertoire"):
            match = s3(r"\b(935)\s*[|/:\-]\s*(\d{2,5})\b", z_final, raw, re.IGNORECASE)
            if match:
                set_if_empty("num_agrement", match.group(1))
                set_if_empty("num_repertoire", match.group(2))
    
        commissaire_match = s3(
            r"Commiss\w*\s+en\s+B\w*[\s\S]{0,80}?\n\s*([^\n]{6,120})",
            z_final,
            raw,
            re.IGNORECASE,
        )
        if commissaire_match:
            commissaire_candidate = re.sub(r"\s+", " ", commissaire_match.group(1)).strip(" -|")
            commissaire_candidate = re.sub(r"\b(N\s*[°o]?\s*agr[ée]ment|r[ée]pertoire|RFP|ICE)\b.*$", "", commissaire_candidate, flags=re.IGNORECASE).strip(" -|")
            if len(re.sub(r"[^A-Za-z]", "", commissaire_candidate)) >= 6:
                set_if_empty("commissaire_douane", commissaire_candidate)
    
        match = s3(r"\b([Dd]\d{2,6}[A-Z]{2,4}\d[A-Z])\b", z_final)
        if match:
            data["cle_authentification"] = match.group(1).upper()
    
        # Validation / security
        match = s3(r"engagement[^\n:]{0,20}[:\-]?\s*([^\n]{5,200})", raw, None, re.IGNORECASE)
        if match:
            engagement_candidate = re.sub(r"\s+", " ", match.group(1)).strip(" -|")
            if 8 <= len(engagement_candidate) <= 140:
                set_if_empty("texte_engagement", engagement_candidate)
    
        if not data.get("texte_engagement"):
            contextual_engagement = s3(
                r"Engagem\w*[\s\S]{0,120}?\n\s*([^\n]{8,140})",
                z_liquidation,
                raw,
                re.IGNORECASE,
            )
            if contextual_engagement:
                engagement_candidate = re.sub(r"\s+", " ", contextual_engagement.group(1)).strip(" -|")
                if not re.search(r"\b(Total|Totaux|Rin[ée]mire|Code\s+GDT)\b", engagement_candidate, re.IGNORECASE):
                    set_if_empty("texte_engagement", engagement_candidate)
    
        match = s3(r"cachet[^\n:]{0,20}[:\-]?\s*([^\n]{2,120})", raw, None, re.IGNORECASE)
        if match:
            set_if_empty("cachet", match.group(1).strip())
    
        match = s3(r"\b(qr\s*code|qrcode)\b[^\n:]{0,20}[:\-]?\s*([^\n]{3,200})", raw, None, re.IGNORECASE)
        if match:
            set_if_empty("qr_code", match.group(2).strip())
    
        match = s3(r"num[eé]ro\s+d\.?a\.?e\.?[^\n:]{0,20}[:\-]?\s*([A-Z0-9\-/]{3,40})", raw, None, re.IGNORECASE)
        if match:
            set_if_empty("numero_dae", match.group(1).strip())
    
        # Addresses
        match = s3(r"([A-Z0-9][^\n]{10,120})\s+Code\b", z_exportateur, None, re.IGNORECASE)
        if match and not data.get("adresse_exportateur"):
            candidate = re.split(r"\r?\n|Code|Num[eé]ro|Date|Pays|Declaration|Dectaration", match.group(1), maxsplit=1)[0].strip()
            if candidate:
                data["adresse_exportateur"] = candidate
    
        match = s3(r"(CL\s?\d{3,6}\s+[A-Z][A-Z\s\.\&\-]{5,50})", z_importateur, None, re.IGNORECASE)
        if match and not data.get("adresse_importateur"):
            candidate = re.split(r"\r?\n|Code|Pays|Déclarant|Declarant|Repertoire|N[eé]credit", match.group(1), maxsplit=1)[0].strip()
            if candidate:
                data["adresse_importateur"] = candidate
    
        if not data.get("adresse_entreposage"):
            match = s3(r"Adresse\s+des\s+lieux\s+d[\W_]*entreposage[^\n]{0,60}(EMP\s+[A-Z]{2,30})", raw, None, re.IGNORECASE)
            if match:
                data["adresse_entreposage"] = re.sub(r"\s+", " ", match.group(1)).strip().upper()
    
        # Aliases for extended catalog keys
        if data.get("exportateur_nom") and not data.get("exportateur"):
            data["exportateur"] = data["exportateur_nom"]
        if data.get("exportateur_code") and not data.get("code_exportateur"):
            data["code_exportateur"] = data["exportateur_code"]
        if data.get("importateur_nom") and not data.get("importateur"):
            data["importateur"] = data["importateur_nom"]
        if data.get("declarant_nom") and not data.get("declarant"):
            data["declarant"] = data["declarant_nom"]
        if data.get("nbre_articles") and not data.get("nombre_articles"):
            data["nombre_articles"] = data["nbre_articles"]
        if data.get("pays_destination") and not data.get("pays_destination_finale"):
            data["pays_destination_finale"] = data["pays_destination"]
        if data.get("mode_transport") and not data.get("transport_international_mode"):
            data["transport_international_mode"] = data["mode_transport"]
        if data.get("date_arrivee_depart") and not data.get("date_validation"):
            data["date_validation"] = data["date_arrivee_depart"]
        if data.get("bureau_douane") and not data.get("designation_bureau"):
            data["designation_bureau"] = data["bureau_douane"]
        if data.get("code_qcs") and not data.get("qcs"):
            data["qcs"] = data["code_qcs"]
        if data.get("declarant_nom") and not data.get("nom_declarant"):
            data["nom_declarant"] = data["declarant_nom"]
        if data.get("designation_marchandises") and not data.get("description_marchandise"):
            data["description_marchandise"] = data["designation_marchandises"]
        if data.get("valeur_fob_dt") and not data.get("valeur_dinars"):
            data["valeur_dinars"] = data["valeur_fob_dt"]
        if data.get("montant_liquidation"):
            if not data.get("montant_total"):
                data["montant_total"] = data["montant_liquidation"]
            if not data.get("total"):
                data["total"] = data["montant_liquidation"]
            if not data.get("totaux"):
                data["totaux"] = data["montant_liquidation"]
        if data.get("importateur_pays") and not data.get("pays_achat"):
            data["pays_achat"] = data["importateur_pays"]
        if data.get("adresse_entreposage") and not data.get("adresse_importateur"):
            data["adresse_importateur"] = data["adresse_entreposage"]
        if data.get("articles") and not data.get("nbre_articles"):
            data["nbre_articles"] = str(len(data["articles"]))
        if data.get("nbre_articles") and not data.get("nombre_articles"):
            data["nombre_articles"] = data["nbre_articles"]
        if not data.get("declarant_code") and data.get("cle_authentification"):
            match = re.search(r"^D(\d{4})", str(data["cle_authentification"]).upper())
            if match:
                data["declarant_code"] = match.group(1)
        if data.get("pays_destination") and not data.get("pays_premiere_destination"):
            data["pays_premiere_destination"] = data["pays_destination"]
    
        if data.get("exportateur_nom"):
            data["exportateur_nom"] = _sanitize_company_name(data["exportateur_nom"])
        if data.get("importateur_nom"):
            data["importateur_nom"] = _sanitize_company_name(data["importateur_nom"])
        if data.get("exportateur"):
            data["exportateur"] = _sanitize_company_name(data["exportateur"])
        if data.get("importateur"):
            data["importateur"] = _sanitize_company_name(data["importateur"])
    
        if data.get("destination"):
            destination_value = str(data["destination"]).strip().upper()
            if destination_value.isalpha() and len(destination_value) < 3:
                data["destination"] = None
    
        if data.get("localisation_export"):
            localisation_value = str(data["localisation_export"]).strip().upper()
            if localisation_value not in {"EXPORT", "IMPORT", "TRANSIT"}:
                data["localisation_export"] = None
    
        if data.get("adresse_exportateur"):
            cleaned_address = re.sub(r"^\d+\s*\|\s*\d+\s*\|\s*", "", str(data["adresse_exportateur"]))
            cleaned_address = re.sub(r"^\d+\s+", "", cleaned_address)
            cleaned_address = re.sub(r"\s+", " ", cleaned_address).strip(" -|")
            address_match = re.search(
                r"(\d{2,4}\s+[A-Z][A-Z]{2,}(?:\s+[A-Z][A-Z]{2,}){1,})",
                cleaned_address,
                re.IGNORECASE,
            )
            if address_match:
                data["adresse_exportateur"] = re.sub(r"\s+", " ", address_match.group(1)).strip()
            else:
                data["adresse_exportateur"] = cleaned_address
    
        if data.get("code_importateur") and not _is_probable_code(data.get("code_importateur")):
            data["code_importateur"] = None
    
        # Normalize transport/mode tokens to canonical forms (e.g. 'BATEAU DU' -> 'BATEAU')
        for tkey in (
            "mode_transport",
            "transport_international_identite",
            "transport_international_mode",
            "transport_national_mode",
            "transport_international_mode",
        ):
            if data.get(tkey):
                try:
                    norm = _normalize_transport_token(data.get(tkey))
                    if norm:
                        data[tkey] = norm
                except Exception:
                    # best-effort normalization; ignore on error
                    pass
    
        return valider_champs(data)


def parse_fields(text, zones_text=None, article_rows=None):
    """Parse OCR text and repair fragile customs-form fields independently.

    The legacy parser contains many useful patterns, but several blocks are gated
    by earlier optional fields. This wrapper keeps the legacy output when useful
    and then applies independent template-aware fallbacks so one missed party name
    no longer prevents the rest of the declaration from being extracted.
    """
    try:
        legacy_data = _legacy_parse_fields(text, zones_text=zones_text, article_rows=article_rows)
    except Exception:
        legacy_data = None

    if isinstance(legacy_data, dict):
        data = legacy_data
        for key, default_value in _empty_result(article_rows=article_rows).items():
            data.setdefault(key, default_value)
    else:
        data = _empty_result(article_rows=article_rows)

    data = _apply_customs_template_fallbacks(
        data,
        text or "",
        zones_text=zones_text or {},
        article_rows=article_rows,
    )
    return valider_champs(data)
