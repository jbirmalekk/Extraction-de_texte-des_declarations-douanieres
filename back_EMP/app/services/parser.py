# Copie exacte de la Cellule 12 du notebook
import re

TYPES_VALIDES   = {"DAE","EA","SE","DUM","IM","IM4","IM6","EX","EX1","EX3","T1"}
DEVISES_VALIDES = {"USD","EUR","GBP","TND","CHF","JPY","CAD"}


def _safe_float(v):
    if v is None: return None
    s = re.sub(r"[^0-9.]", "", str(v).replace(",",".").replace(" ",""))
    try: return float(s) if s else None
    except: return None


def valider_champs(data):
    score, total, flags = 0, 0, []

    def check(cond, label, w=1):
        nonlocal score, total
        total += w
        if cond: score += w
        else: flags.append(label)

    num = data.get("numero_declaration")
    check(bool(num and re.fullmatch(r"\d{6}", str(num))),
          "numero_declaration", 3)

    date = data.get("date_declaration")
    check(bool(date and re.search(r"\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4}",
               str(date))), "date_declaration", 2)

    typ = str(data.get("type_declaration","")).upper().replace(".","").replace(" ","")
    check(bool(typ and typ in TYPES_VALIDES), "type_declaration", 2)

    dev = str(data.get("devise","")).upper().strip()
    check(bool(not dev or dev in DEVISES_VALIDES), "devise", 2)

    exp = data.get("exportateur_nom")
    check(bool(exp and len(re.sub(r"[^A-Za-z]","",str(exp))) >= 5),
          "exportateur_nom", 2)

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
    check(bool(cle and re.fullmatch(r"[A-Z0-9]{10,12}", str(cle))),
          "cle_authentification", 1)

    pct = round(score / total * 100) if total > 0 else 0
    data["score_confiance"]  = pct
    data["flags_validation"] = flags
    data["qualite"] = "HAUT" if pct >= 80 else ("MOYEN" if pct >= 50 else "BAS")
    return data


def parse_fields(text, zones_text=None, article_rows=None):
    raw = text
    z   = zones_text or {}

    z_header       = z.get("header",       raw)
    z_exportateur  = z.get("exportateur",  raw)
    z_importateur  = z.get("importateur",  raw)
    z_declarant    = z.get("declarant",    raw)
    z_conditions   = z.get("conditions",   raw)
    z_finances     = z.get("finances",     raw)
    z_marchandises = z.get("marchandises", raw)
    z_taxes        = z.get("taxes",        raw)
    z_liquidation  = z.get("liquidation",  raw)
    z_final        = z.get("final",        raw)

    data = {
        "numero_declaration": None, "date_declaration": None,
        "type_declaration": None,   "nbre_articles": None,
        "exportateur_nom": None,    "exportateur_code": None,
        "importateur_nom": None,    "importateur_pays": None,
        "declarant_code": None,     "declarant_nom": None,
        "mode_transport": None,     "date_arrivee_depart": None,
        "pays_provenance": None,    "pays_destination": None,
        "adresse_entreposage": None,"mode_livraison": None,
        "devise": None,             "montant_ptfn": None,
        "valeur_fob_dt": None,      "taux_conversion": None,
        "designation_marchandises": None,
        "poids_brut": None,         "poids_net": None,
        "taxes": [],                "articles": article_rows or [],
        "bureau_douane": None,      "code_gdt": None,
        "montant_liquidation": None,"itineraire": None,
        "num_agrement": None,       "num_repertoire": None,
        "cle_authentification": None,
    }

    def s3(pat, z1, z2=None, fl=0):
        for src in [z1, z2, raw]:
            if src:
                m = re.search(pat, src, fl)
                if m: return m
        return None

    # header
    m = s3(r'\b(\d{6})\b', z_header)
    if m: data["numero_declaration"] = m.group(1)

    dates = re.findall(r'\b(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})\b', raw)
    if dates: data["date_declaration"] = dates[0]
    if len(dates) >= 2: data["date_arrivee_depart"] = dates[1]

    m = s3(r'\b(D\.?A\.?E\.?|E\.?A\.?|S\.?E\.?|D\.?U\.?M\.?|IM\s?\d{1,3}|EX\s?\d{1,3})\b',
           z_header, None, re.IGNORECASE)
    if m: data["type_declaration"] = re.sub(r'\.','',m.group(1)).strip().upper()

    m = s3(r'nbre\s+tot[^\d]{0,15}(\d{1,3})', z_header, None, re.IGNORECASE)
    if not m: m = s3(r'\bEA\s+(\d{1,3})\b', z_header)
    if m: data["nbre_articles"] = m.group(1)

    # exportateur
    m = s3(r'(?:\d{4}:)([A-Z][A-Z\s\.\&]{5,60})', z_exportateur, None, re.IGNORECASE)
    if m: data["exportateur_nom"] = m.group(1).strip()
    m = s3(r'\b(\d{6,7}[A-Z])\b', z_exportateur)
    if m: data["exportateur_code"] = m.group(1)

    # importateur
    m = s3(r'(CL\d{3,6}\s+[A-Z][A-Z\s\.\&\-]{5,50})',
           z_importateur, None, re.IGNORECASE)
    if m:
        data["importateur_nom"] = re.split(r'\n|Code|Adresse',
                                           m.group(1))[0].strip()
    m = s3(r'\b(U\.?S\.?A\.?|ALLEMAGNE|FRANCE|ITALIE|ESPAGNE|CHINE|TURQUIE|BELGIQUE|PAYS\s+BAS|ROYAUME\s+UNI)\b',
           z_importateur, None, re.IGNORECASE)
    if m: data["importateur_pays"] = re.sub(r'\.','',m.group(1)).strip().upper()

    m = s3(r'(?:entreposage|lieux\s+d.entreposage)[^\n]{0,20}\n([^\n]{10,100})',
           z_importateur, None, re.IGNORECASE)
    if m: data["adresse_entreposage"] = re.sub(r'^[\|\s\d\W]{0,5}','',m.group(1)).strip()

    # declarant
    m = s3(r'd[eé]clarant[^\n]{0,15}(\d{4})\b', z_declarant, None, re.IGNORECASE)
    if m: data["declarant_code"] = m.group(1)
    m = re.search(r'(STE\s+SMART\s+CUSTOMS[A-Z\s]{0,20})', raw, re.IGNORECASE)
    if m: data["declarant_nom"] = re.split(r'\s+(?:PS|Pays|Go|pres|BR)',
                                            m.group(1))[0].strip()

    # conditions
    m = s3(r'\b(IT\s?\d{2,4}|BATEAU\s+DU|CAMION|VOL\s+DU|AVION|M0[A-Z0-9]+)\b',
           z_conditions, None, re.IGNORECASE)
    if m: data["mode_transport"] = m.group(1).strip().upper()
    m = s3(r'\b(EXW|CFR|DAP|FOB|CIF|CIP|CPT|DDP|FCA|FAS|DAT)\b', z_conditions)
    if m: data["mode_livraison"] = m.group(1).upper()

    m = s3(r'(TUNISIE|USA|ALLEMAGNE|FRANCE|ITALIE|ESPAGNE|CHINE|TURQUIE|BELGIQUE)'
           r'\s+(?:TN|US|DE|FR|IT|ES|CN|TR|BE)\s+\1', raw, None, re.IGNORECASE)
    if not m: m = s3(r'provenance[^\n]{0,60}\n\s*(TUNISIE|USA|ALLEMAGNE|FRANCE|ITALIE)',
                     raw, None, re.IGNORECASE)
    if m: data["pays_provenance"] = m.group(1).strip().upper()

    m = s3(r'destination\s+d[eé]finitive[^\n]{0,30}\n\s*([A-Z]{2,}(?:\s+[A-Z]{2,})?)',
           raw, None, re.IGNORECASE)
    if not m: m = s3(r'\b(PAYS\s+BAS|ROYAUME\s+UNI|TUNISIE|FRANCE|ALLEMAGNE|USA|ITALIE|ESPAGNE|BELGIQUE)\b',
                     raw, None, re.IGNORECASE)
    if m: data["pays_destination"] = m.group(1).strip().upper()

    # finances
    for src in [z_finances, raw]:
        if not src: continue
        m1 = re.search(r'\d{2}[-\/]\d{2}[-\/]\d{4}[^\n]{0,40}(USD|EUR|GBP|TND|CHF)[^\n\d]{0,5}(\d{3,10}[.,]\d{3})', src)
        m2 = re.search(r'\b(USD|EUR|GBP|TND|CHF)\b[^\n\d]{0,10}(\d{3,10}[.,]\d{3})', src)
        m3 = re.search(r'(?:PTFN|PTEN|PIFN)[^\n]{0,100}(\d{4,10}[.,]\d{3})', src, re.IGNORECASE)
        if m1:
            data["devise"] = m1.group(1).upper()
            data["montant_ptfn"] = m1.group(2).replace(',','.')
            break
        elif m2:
            data["devise"] = m2.group(1).upper()
            data["montant_ptfn"] = m2.group(2).replace(',','.')
            break
        elif m3:
            data["montant_ptfn"] = m3.group(1).replace(',','.')

    for src in [z_finances, raw]:
        if not src: continue
        m = re.search(r'dinars[^\n]{0,30}\n[^\n]{0,30}?(\d{4,10}[.,]\d{3})', src, re.IGNORECASE)
        if not m: m = re.search(r'facturation\)[^\n]{0,10}\n(\d{4,10}[.,]\d{3})', src, re.IGNORECASE)
        if m: data["valeur_fob_dt"] = m.group(1).replace(',','.'); break

    m = s3(r'\b(\d{1,2}[.,]\d{6,8})\b', z_finances)
    if m: data["taux_conversion"] = m.group(1).replace(',','.')

    # marchandises
    m = s3(r'd[eé]signation\s+des\s+marchandises[^\n]{0,30}\n([^\n]{5,100})',
           z_marchandises, None, re.IGNORECASE)
    if m: data["designation_marchandises"] = re.sub(r'^[\|\s\W]{0,5}','',m.group(1)).strip()
    m = s3(r'Poids\s+brut[^\d\n]{0,40}(\d{2,6})', z_marchandises, None, re.IGNORECASE)
    if m: data["poids_brut"] = m.group(1)
    m = s3(r'Poids\s+net[^\d\n]{0,40}(\d{2,6})', z_marchandises, None, re.IGNORECASE)
    if m: data["poids_net"] = m.group(1)

    # taxes
    for src in [z_taxes, raw]:
        if not src: continue
        found = re.findall(
            r'\b(\d{3})\s+(\d{1,10}[.,]\d{3})\s+(\d{1,6}[.,]\d{6})\s+(\d{1,10}[.,]\d{3})',
            src
        )
        if found:
            data["taxes"] = [{"code":t[0],"assiette":t[1].replace(',','.'),
                               "quotite":t[2].replace(',','.'),"montant":t[3].replace(',','.')}
                              for t in found]
            break

    # liquidation
    m = s3(r'\b(BR[\-\s]?ARIANA|BR[\-\s]?TUNIS|BR[\-\s]?SFAX|TUNIS|BIZERTE|SFAX)\b',
           z_liquidation, None, re.IGNORECASE)
    if m: data["bureau_douane"] = m.group(0).upper().strip()
    m = s3(r'\b(?:Total|Totaux)\b\s+(\d{1,8}[.,]\d{3})', z_liquidation, None, re.IGNORECASE)
    if m: data["montant_liquidation"] = m.group(1).replace(',','.')
    m = s3(r'(?:GDT|Code\s+GDT)[^\d]{0,10}(\d{3})', z_liquidation, None, re.IGNORECASE)
    if m: data["code_gdt"] = m.group(1)

    # final
    m = s3(r'\b([A-Z]{2,6}[\-][A-Z]{2,6})\b', z_final)
    if m: data["itineraire"] = m.group(1)
    m = s3(r'935\s+(\d{2,5})', z_final)
    if m: data["num_agrement"] = "935"; data["num_repertoire"] = m.group(1)
    m = s3(r'\b([Dd]\d{4}[A-Z]{3}\d[A-Z])\b', z_final)
    if m: data["cle_authentification"] = m.group(1).upper()

    return valider_champs(data)