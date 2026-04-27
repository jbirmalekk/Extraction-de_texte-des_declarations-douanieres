import re

TYPES_VALIDES = {"DAE", "EA", "SE", "DUM", "IM", "IM4", "IM6", "EX", "EX1", "EX3", "T1"}
DEVISES_VALIDES = {"USD", "EUR", "GBP", "TND", "CHF", "JPY", "CAD"}
COUNTRY_BY_CODE = {
    "TN": "TUNISIE",
    "DE": "ALLEMAGNE",
    "FR": "FRANCE",
    "IT": "ITALIE",
    "ES": "ESPAGNE",
    "BE": "BELGIQUE",
    "US": "USA",
    "CN": "CHINE",
    "TR": "TURQUIE",
    "NL": "PAYS BAS",
    "GB": "ROYAUME UNI",
}


def _safe_float(value):
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9.]", "", str(value).replace(",", ".").replace(" ", ""))
    try:
        return float(cleaned) if cleaned else None
    except Exception:
        return None


def _extract_articles_from_text(text):
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


def valider_champs(data):
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
    check(bool(typ and typ in TYPES_VALIDES), "type_declaration", 2)

    dev = str(data.get("devise", "")).upper().strip()
    check(bool(not dev or dev in DEVISES_VALIDES), "devise", 2)

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
    check(bool(cle and re.fullmatch(r"[A-Z0-9]{10,12}", str(cle))), "cle_authentification", 1)

    pct = round(score / total * 100) if total > 0 else 0
    data["score_confiance"] = pct
    data["flags_validation"] = flags
    data["qualite"] = "HAUT" if pct >= 80 else ("MOYEN" if pct >= 50 else "BAS")
    return data


def parse_fields(text, zones_text=None, article_rows=None):
    raw = text or ""
    zones = zones_text or {}

    z_header = zones.get("header", raw)
    z_exportateur = zones.get("exportateur", raw)
    z_importateur = zones.get("importateur", raw)
    z_declarant = zones.get("declarant", raw)
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
        "numero_titre_ce": None,
        "code_regime_precedent": None,
        "code_regime_financier": None,
        "code_delai": None,
        "code_oci": None,
        "douane": None,
        "coefficient_ajustement": None,
        "description_marchandise": None,
        "bureau_frontiere": None,
        "destination": None,
        "localisation_export": None,
        "taxes": article_rows or _extract_articles_from_text(raw),
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

    # Header
    match = s3(r"\b(\d{6})\b", z_header)
    if match:
        data["numero_declaration"] = match.group(1)

    dates = re.findall(r"\b(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})\b", raw)
    if dates:
        data["date_declaration"] = dates[0]
    if len(dates) >= 2:
        data["date_arrivee_depart"] = dates[1]

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

    match = s3(r"\b(?:N(?:bre|ore)?\s*total\s*(?:colis|coils|cohs)|nbre\s*colis)\b[^\d]{0,20}(\d{1,3})", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("nombre_colis", match.group(1))

    match = s3(r"\b(?:r[eé]pertoire)\b[^\d]{0,20}(\d{2,6})", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("repertoire", match.group(1))

    match = s3(r"\b(?:n[°o]?\s*cr[eé]dit|num[eé]ro\s+cr[eé]dit)\b[^\d]{0,20}(\d{2,10})", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("numero_credit", match.group(1))

    # Exportateur
    match = s3(r"(?:\d{4}:)([A-Z][A-Z\s\.\&]{5,120})", z_exportateur, None, re.IGNORECASE)
    if match:
        exportateur_nom = re.split(
            r"\r?\n|Dectaration|Declaration|Certificat|Code|Num[eé]ro|Date|Pays",
            match.group(1),
            maxsplit=1,
        )[0].strip()
        data["exportateur_nom"] = re.sub(r"\s+", " ", exportateur_nom)
    match = s3(r"\b(\d{6,8}[A-Z])\b", z_exportateur, None, re.IGNORECASE)
    if match:
        data["exportateur_code"] = match.group(1).upper()

    # Importateur
    match = s3(r"(CL\d{3,6}\s+[A-Z][A-Z\s\.\&\-]{5,50})", z_importateur, None, re.IGNORECASE)
    if match:
        importateur_nom = re.split(r"\n|\bEMP\b|Code|Adresse|Pays|Repertoire|N[eé]?credit", match.group(1), maxsplit=1)[0].strip()
        data["importateur_nom"] = re.sub(r"\s+", " ", importateur_nom)
    match = s3(r"\b(CL\d{3,6})\b", z_importateur, None, re.IGNORECASE)
    if match:
        data["code_importateur"] = match.group(1).upper()
    match = s3(r"\b(U\.?S\.?A\.?|ALLEMAGNE|FRANCE|ITALIE|ESPAGNE|CHINE|TURQUIE|BELGIQUE|PAYS\s+BAS|ROYAUME\s+UNI)\b", z_importateur, None, re.IGNORECASE)
    if match:
        data["importateur_pays"] = re.sub(r"\.", "", match.group(1)).strip().upper()
    match = s3(r"(?:entreposage|lieux\s+d[\W_]*entreposage)[\s\S]{0,80}?\n([^\n]{10,120})", z_importateur, None, re.IGNORECASE)
    if match:
        data["adresse_entreposage"] = re.sub(r"^[\|\s\d\W]{0,8}", "", match.group(1)).strip()

    # Declarant
    match = s3(r"d[eé]clarant[^\n]{0,15}(\d{4})\b", z_declarant, None, re.IGNORECASE)
    if match:
        data["declarant_code"] = match.group(1)
    match = re.search(r"(STE\s+SMART\s+CUSTOMS[A-Z\s]{0,20})", raw, re.IGNORECASE)
    if match:
        data["declarant_nom"] = re.split(r"\s+(?:PS|Pays|Go|pres|BR)", match.group(1))[0].strip()

    # Transport
    match = s3(r"\b(IT\s?\d{2,4}|BATEAU\s+DU|CAMION|VOL\s+DU|AVION|M0[A-Z0-9]+)\b", z_conditions, None, re.IGNORECASE)
    if match:
        data["mode_transport"] = match.group(1).strip().upper()
    match = s3(r"\b(EXW|CFR|DAP|FOB|CIF|CIP|CPT|DDP|FCA|FAS|DAT)\b", z_conditions)
    if match:
        data["mode_livraison"] = match.group(1).upper()

    match = s3(r"\b(VOL\s+DU|BATEAU\s+DU|CAMION\s+DU|TRAIN\s+DU)\b", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("transport_international_identite", match.group(1).strip().upper())

    match = s3(r"moyen\s+de\s+transport[\s\S]{0,120}?etrang(?:er|ere)[\s\S]{0,120}?(BATEAU\s+DU|VOL\s+DU|CAMION|AVION)", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("transport_international_identite", match.group(1).strip().upper())

    match = s3(r"moyen\s+de\s+transport[\s\S]{0,160}?national[\s\S]{0,120}?(CAMION|TRAIN|ROUTIER)", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("transport_national_mode", match.group(1).strip().upper())

    match = s3(r"transport\s+international[^\n]{0,120}(a[eé]rien|maritime|routier|ferroviaire|camion|avion|bateau)", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("transport_international_mode", match.group(1).strip().upper())

    match = s3(r"transport\s+national[^\n]{0,120}(camion|routier|ferroviaire|rail)", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("transport_national_mode", match.group(1).strip().upper())

    match = s3(r"nationalit[eé][^\n]{0,40}(tunisie|france|allemagne|italie|espagne|usa|chine|turquie|belgique)", raw, None, re.IGNORECASE)
    if match:
        nationality = match.group(1).strip().upper()
        set_if_empty("transport_international_nationalite", nationality)
        set_if_empty("transport_national_nationalite", nationality)

    match = s3(r"nationalit[eé][\s\S]{0,120}?(TN|DE|FR|IT|ES|BE|US|CN|TR|NL|GB)\b", raw, None, re.IGNORECASE)
    if match:
        country = COUNTRY_BY_CODE.get(match.group(1).upper())
        if country:
            set_if_empty("transport_international_nationalite", country)
            set_if_empty("transport_national_nationalite", country)

    if not data.get("pays_provenance"):
        match = s3(r"pays\s+de\s+pro\w*[\s\S]{0,120}?(TN|US|DE|FR|IT|ES|BE|CN|TR|NL|GB)\b", raw, None, re.IGNORECASE)
        if match:
            data["pays_provenance"] = COUNTRY_BY_CODE.get(match.group(1).upper(), match.group(1).upper())

    match = s3(r"pays\s+de\s+pro\w*[^A-Z0-9]{0,30}(TN|DE|FR|IT|ES|BE|US|CN|TR|NL|GB)\b", raw, None, re.IGNORECASE)
    if match and not data.get("pays_provenance"):
        data["pays_provenance"] = COUNTRY_BY_CODE.get(match.group(1).upper())

    match = s3(r"pays\s+de\s+premi\w*\s+dest\w*[^A-Z0-9]{0,30}(TN|DE|FR|IT|ES|BE|US|CN|TR|NL|GB)", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("pays_premiere_destination", COUNTRY_BY_CODE.get(match.group(1).upper()))

    match = s3(r"destination\s+d[eé]finitive[^\n]{0,30}\n\s*([A-Z]{2,}(?:\s+[A-Z]{2,})?)", raw, None, re.IGNORECASE)
    if not match:
        match = s3(r"\b(PAYS\s+BAS|ROYAUME\s+UNI|TUNISIE|FRANCE|ALLEMAGNE|USA|ITALIE|ESPAGNE|BELGIQUE)\b", raw, None, re.IGNORECASE)
    if match:
        data["pays_destination"] = match.group(1).strip().upper()

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

    match = s3(r"mode\s+de\s+paiement[^\n:]{0,20}[:\-]?\s*([^\n]{2,60})", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("mode_paiement", match.group(1).strip())

    match = s3(r"relation\s+acheteur\s*/?\s*vendeur[^\n:]{0,20}[:\-]?\s*([^\n]{2,80})", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("relation_acheteur_vendeur", match.group(1).strip())

    match = s3(r"valeur\s+totale[^\d]{0,20}(\d{1,12}(?:[.,]\d{1,3})?)", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("valeur_totale", match.group(1).replace(",", "."))

    match = s3(r"assurance[^\d]{0,20}(\d{1,12}(?:[.,]\d{1,3})?)", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("assurance", match.group(1).replace(",", "."))

    match = s3(r"\bfret\b[^\d]{0,20}(\d{1,12}(?:[.,]\d{1,3})?)", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("fret", match.group(1).replace(",", "."))

    match = s3(r"valeur\s+en\s+dinars[^\d]{0,20}(\d{2,12}(?:[.,]\d{3,4})?)", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("valeur_dinars", match.group(1).replace(",", "."))

    match = s3(r"valeur\s+douane\s+totale[^\d]{0,30}(\d{2,12}(?:[.,]\d{3,4})?)", raw, None, re.IGNORECASE)
    if match:
        amount = norm_amount(match.group(1))
        set_if_empty("valeur_dinars", amount)
        set_if_empty("valeur_totale", amount)

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
        set_if_empty("pfn", match.group(2))
        set_if_empty("valeur_prise_en_charge", norm_amount(match.group(3)))

    match = s3(r"\b(?:Code\s*)?(?:QCS|OCS|ACS)\b[\s\S]{0,120}?(\d{1,3})\s+(\d{1,4})\s+(\d{1,12}(?:[.,]\d{3,4})?)", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("code_qcs", match.group(1))
        set_if_empty("pfn", match.group(2))
        set_if_empty("valeur_prise_en_charge", norm_amount(match.group(3)))

    if not data.get("code_qcs") or not data.get("pfn"):
        match = s3(r"\b(\d{1,3})\s+(\d{1,4})\s+(\d{1,12}(?:[.,]\d{3,4})?)\b", raw, None, re.IGNORECASE)
        if match and data.get("code_sh_ndp") and data.get("code_pays_origine"):
            set_if_empty("code_qcs", match.group(1))
            set_if_empty("pfn", match.group(2))
            set_if_empty("valeur_prise_en_charge", norm_amount(match.group(3)))

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

    match = s3(r"\b(?:Total|Totaux)\b\s+(\d{1,12}(?:[.,]\d{3,4})?)", z_liquidation, None, re.IGNORECASE)
    if match:
        data["montant_liquidation"] = match.group(1).replace(",", ".")

    match = s3(r"(?:GDT|Code\s+GDT)[^\d]{0,10}(\d{3})", z_liquidation, None, re.IGNORECASE)
    if match:
        data["code_gdt"] = match.group(1)

    match = s3(r"\bN\s*[°o]?\s*d[\'’]?escale\b[^\d]{0,20}(\d{1,6})", z_liquidation, None, re.IGNORECASE)
    if match:
        set_if_empty("bureau_frontiere", match.group(1))

    match = s3(r"\bLocalisation\b[^A-Z0-9]{0,20}([A-Z]{3,20})\b", z_liquidation, None, re.IGNORECASE)
    if match:
        set_if_empty("localisation_export", match.group(1).upper())

    match = s3(r"\bDestination\b[^A-Z0-9]{0,20}([A-Z]{2,20}|\d{1,4})\b", z_liquidation, None, re.IGNORECASE)
    if match:
        set_if_empty("destination", match.group(1).upper())

    # Final
    match = s3(r"\b([A-Z]{2,6}[\-][A-Z]{2,6})\b", z_final)
    if match:
        data["itineraire"] = match.group(1)

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

    match = s3(r"\b([Dd]\d{4}[A-Z]{3}\d[A-Z])\b", z_final)
    if match:
        data["cle_authentification"] = match.group(1).upper()

    # Validation / security
    match = s3(r"engagement[^\n:]{0,20}[:\-]?\s*([^\n]{5,200})", raw, None, re.IGNORECASE)
    if match:
        set_if_empty("texte_engagement", match.group(1).strip())

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

    match = s3(r"CL\d{3,6}\s+[A-Z][A-Z\s\.\&\-]{5,50}[\s\S]{0,80}?\n\n([A-Z0-9][^\n]{5,80})\n\nCode\b", z_importateur, None, re.IGNORECASE)
    if match and not data.get("adresse_importateur"):
        candidate = re.split(r"\r?\n|Code|Pays|Déclarant|Declarant|Repertoire|N[eé]credit", match.group(1), maxsplit=1)[0].strip()
        if candidate:
            data["adresse_importateur"] = candidate

    if not data.get("adresse_entreposage") and data.get("adresse_importateur"):
        data["adresse_entreposage"] = data["adresse_importateur"]

    if not data.get("adresse_entreposage"):
        match = s3(r"Adresse\s+des\s+lieux\s+d[\W_]*entreposage[\s\S]{0,180}?([A-Z0-9][^\n]{8,120})", raw, None, re.IGNORECASE)
        if match:
            candidate = re.split(r"\r?\n|Code|Pays|Déclarant|Declarant|Repertoire|N[eé]credit", match.group(1), maxsplit=1)[0].strip()
            if candidate:
                data["adresse_entreposage"] = candidate

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
    if data.get("declarant_nom") and not data.get("nom_declarant"):
        data["nom_declarant"] = data["declarant_nom"]
    if data.get("valeur_fob_dt") and not data.get("valeur_dinars"):
        data["valeur_dinars"] = data["valeur_fob_dt"]
    if data.get("pays_destination") and not data.get("pays_premiere_destination"):
        data["pays_premiere_destination"] = data["pays_destination"]

    return valider_champs(data)
