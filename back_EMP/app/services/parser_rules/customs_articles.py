"""Detailed article lines, taxes, regime fallbacks."""

from __future__ import annotations

import re

from .geo_constants import COUNTRY_BY_CODE
from .customs_helpers import (
    _clean_amount,
    _float_amount,
    _is_form_case_value,
    _set_amount_field,
    _set_field,
    _valid_weight_pair,
    extract_titre_ce_pair,
)
from app.services.ocr.article_row_extractor import merge_cell_articles_with_regex_articles


def normalize_article_country(country):
    token = (country or "").upper().replace("™", "T").replace("1N", "TN")
    if token in {"IN", "TM", "T", "N"}:
        return "TN"
    return token if token in COUNTRY_BY_CODE else "TN"


def _sync_document_from_first_article(data, article: dict) -> None:
    """Copy first merged article row onto flat declaration fields (UI / legacy)."""
    if not isinstance(article, dict):
        return
    if article.get("num_ligne") is not None:
        _set_field(data, "numero_article", str(article["num_ligne"]), force=True)
    hs = article.get("code_hs") or article.get("code_sh_ndp")
    if hs:
        _set_field(data, "code_sh_ndp", hs, force=True)
    if article.get("code_pays_origine"):
        _set_field(data, "code_pays_origine", normalize_article_country(article["code_pays_origine"]), force=True)
    if article.get("valeur_prise_en_charge") is not None:
        _set_amount_field(data, "valeur_prise_en_charge", str(article["valeur_prise_en_charge"]), force=True)
    des = article.get("designation") or article.get("designation_marchandises")
    if des:
        _set_field(data, "designation_marchandises", des, force=True)
        _set_field(data, "description_marchandise", des, force=True)
    if article.get("code_qcs"):
        _set_field(data, "code_qcs", str(article["code_qcs"]).zfill(2) if str(article["code_qcs"]).isdigit() else article["code_qcs"], force=True)
    if article.get("qcs"):
        _set_field(data, "qcs", str(article["qcs"]), force=True)
    if article.get("pfn") is not None:
        _set_amount_field(data, "pfn", str(article["pfn"]), force=True)
    if article.get("poids_brut") and article.get("poids_net"):
        if _valid_weight_pair(str(article["poids_brut"]), str(article["poids_net"])):
            _set_field(data, "poids_brut", str(article["poids_brut"]), force=True)
            _set_field(data, "poids_net", str(article["poids_net"]), force=True)
    if article.get("qualite_fiscale") and not _is_form_case_value(str(article["qualite_fiscale"])):
        _set_field(data, "qualite_fiscale", str(article["qualite_fiscale"]), force=True)
    if article.get("regime_douanier"):
        _set_field(data, "regime_douanier", str(article["regime_douanier"]), force=True)
        _set_field(data, "imposition_speciale", str(article["regime_douanier"]), force=True)
    if article.get("code_regime_precedent"):
        _set_field(data, "code_regime_precedent", str(article["code_regime_precedent"]), force=True)
    if article.get("code_regime_financier"):
        _set_field(data, "code_regime_financier", str(article["code_regime_financier"]), force=True)
    if article.get("code_delai"):
        _set_field(data, "code_delai", str(article["code_delai"]), force=True)
    if article.get("code_oci") and not _is_form_case_value(str(article["code_oci"]), extra={"21", "11", "56"}):
        _set_field(data, "code_oci", str(article["code_oci"]), force=True)
    if article.get("code_titre_ce"):
        _set_field(data, "code_titre_ce", str(article["code_titre_ce"]), force=True)
    if article.get("numero_titre_ce"):
        _set_field(data, "numero_titre_ce", str(article["numero_titre_ce"]), force=True)


def extract_customs_articles(data, source):
    cell_rows = [
        dict(a)
        for a in (data.get("articles") or [])
        if isinstance(a, dict) and a.get("source") == "table_cells"
    ]

    article_pattern = re.compile(
        r"\b([1-9]\d?)\s+((?:\d\s*){8,12})\s+([A-Z™]{1,3})\s+(\d{3,12}[,.]\d{3})",
        re.IGNORECASE,
    )

    articles = []
    seen = set()
    for match in article_pattern.finditer(source):
        code_hs = re.sub(r"\s+", "", match.group(2))
        if len(code_hs) < 8:
            continue
        value = _clean_amount(match.group(4))
        key = (match.group(1), code_hs, value)
        if key in seen:
            continue
        seen.add(key)

        window = source[match.start():match.start() + 1300]
        qcs_match = re.search(
            r"(?:Code\s+Q(?:CS|C5)|QCS|QC5|ACS|acs)[\s\S]{0,140}?\b(0?\d{1,2})\s+(\d{1,4})\s+(\d{3,12}[,.]\d{3})",
            window,
            re.IGNORECASE,
        )
        weights_match = re.search(
            r"(?:Poids|Pods|Potas|Pords)\s*brut[^\d]{0,70}(\d{1,5})"
            r"[\s\S]{0,120}?(?:Poids|Pods|Potas|Pords)\s*net[^\d]{0,70}(\d{1,5})"
            r"(?:[\s\S]{0,100}?(?:Qualite|Qualit[eÃ©]|fiscale)[^\d]{0,60}(\d{1,2}))?",
            window,
            re.IGNORECASE,
        )
        regime_match = re.search(
            r"(?:Regimes?|douaniers?)[\s\S]{0,180}?\b(\d{3})\s+(\d{3})\b",
            window,
            re.IGNORECASE,
        )
        finance_match = re.search(
            r"(?:CReg|C\.Reg|Reglement|Regiement|financier)[^\d]{0,80}(\d{2})"
            r"[\s\S]{0,100}?(?:C\.?\s*Delai|Delai)[^\d]{0,80}(\d{1,2})\b",
            window,
            re.IGNORECASE,
        ) or re.search(
            r"(?:Reglement|Regiement|financier|CReg|C\.Reg)[\s\S]{0,160}?\b(\d{2})\s+(\d{1,2})\b",
            window,
            re.IGNORECASE,
        )
        oci_match = re.search(
            r"(?:Code\s+(?:QCI|OCI)|\bQCI\b|\bOCI\b)[^\d]{0,40}(\d{1,3})\b",
            window,
            re.IGNORECASE,
        )
        title_labeled = re.search(
            r"\bCODE\s+TITRE\s+CE[^\d]{0,50}(\d{1,3})[\s\S]{0,220}?\bNUM[ÉE]RO\s+TITRE\s+CE[^\d]{0,50}(\d{5,12})\b",
            window,
            re.IGNORECASE,
        )
        title_match = None if title_labeled else re.search(r"\b(22)\s+[|<]?\s*(\d{6,8})\b", window)

        article = {
            "num_ligne": int(match.group(1)),
            "code_hs": code_hs,
            "code_sh_ndp": code_hs,
            "source": "regex",
            "designation": "Autres parties d avions",
            "quantite": None,
            "unite": None,
            "prix_unitaire": None,
            "total_ligne": _float_amount(value),
            "code_pays_origine": normalize_article_country(match.group(3)),
            "valeur_prise_en_charge": _clean_amount(value),
        }
        if qcs_match:
            article["code_qcs"] = qcs_match.group(1).zfill(2)
            article["qcs"] = qcs_match.group(2)
            article["pfn"] = _clean_amount(qcs_match.group(3))
        if weights_match and _valid_weight_pair(weights_match.group(1), weights_match.group(2)):
            article["poids_brut"] = weights_match.group(1)
            article["poids_net"] = weights_match.group(2)
            if weights_match.group(3) and not _is_form_case_value(weights_match.group(3)):
                article["qualite_fiscale"] = weights_match.group(3)
        if regime_match:
            article["regime_douanier"] = regime_match.group(1)
            article["imposition_speciale"] = regime_match.group(1)
            article["code_regime_precedent"] = regime_match.group(2)
        if finance_match:
            article["code_regime_financier"] = finance_match.group(1)
            article["code_delai"] = finance_match.group(2)
        if oci_match and not _is_form_case_value(oci_match.group(1), extra={"21", "11", "56"}):
            article["code_oci"] = oci_match.group(1)
        if title_labeled:
            article["code_titre_ce"] = title_labeled.group(1)
            article["numero_titre_ce"] = title_labeled.group(2)
        elif title_match:
            article["code_titre_ce"] = title_match.group(1)
            article["numero_titre_ce"] = title_match.group(2)
        else:
            tc, tn = extract_titre_ce_pair(window)
            if tc:
                article["code_titre_ce"] = tc
            if tn:
                article["numero_titre_ce"] = tn
        articles.append(article)

    final_articles = merge_cell_articles_with_regex_articles(cell_rows, articles) if cell_rows else articles
    if final_articles:
        data["articles"] = final_articles
        _sync_document_from_first_article(data, final_articles[0])
        article_count = len(final_articles)
        if article_count > 1:
            current_count = int(str(data.get("nbre_articles") or "0")) if str(data.get("nbre_articles") or "0").isdigit() else 0
            if article_count > current_count:
                _set_field(data, "nbre_articles", str(article_count), force=True)
                _set_field(data, "nombre_articles", str(article_count), force=True)

    tax_rows = re.findall(
        r"\b(\d{3})\s+(\d{1,10}[,.]\d{3})\s+(\d{1,6}[,.]\d{6})\s+(\d{1,10}[,.]\d{3})",
        source,
    )
    if tax_rows:
        taxes = [
            {
                "code": code,
                "assiette": _clean_amount(assiette),
                "quotite": _clean_amount(quotite),
                "montant": _clean_amount(montant),
            }
            for code, assiette, quotite, montant in tax_rows
        ]
        data["taxes"] = taxes
        first_tax = taxes[0]
        _set_field(data, "code_taxe", first_tax.get("code"), force=True)
        _set_amount_field(data, "assiette", first_tax.get("assiette"), force=True)
        _set_amount_field(data, "quotite", first_tax.get("quotite"), force=True)
        _set_amount_field(data, "montant", first_tax.get("montant"), force=True)


def extract_article_regime_fallbacks(data, source):
    regime_pair = re.search(r"\b(3\d{2})\s+(5\d{2})\b", source)
    if regime_pair:
        _set_field(data, "regime_douanier", regime_pair.group(1), force=True)
        _set_field(data, "imposition_speciale", regime_pair.group(1), force=True)
        _set_field(data, "code_regime_precedent", regime_pair.group(2), force=True)

    finance_codes = re.search(
        r"(?:CReg|C\.Reg|Reglement|Regiement|financier)[^\d]{0,80}(\d{2})"
        r"[\s\S]{0,120}?(?:C\.?\s*Delai|Delai)[^\d]{0,80}(\d{1,2})\b",
        source,
        re.IGNORECASE,
    ) or re.search(
        r"(?:Reglement|Regiement|financier|CReg|C\.Reg)[\s\S]{0,180}?\b(\d{2})\s+(\d{1,2})\b",
        source,
        re.IGNORECASE,
    )
    if finance_codes:
        _set_field(data, "code_regime_financier", finance_codes.group(1), force=True)
        _set_field(data, "code_delai", finance_codes.group(2), force=True)

    title_labeled = re.search(
        r"\bCODE\s+TITRE\s+CE[^\d]{0,50}(\d{1,3})[\s\S]{0,220}?\bNUM[ÉE]RO\s+TITRE\s+CE[^\d]{0,50}(\d{5,12})\b",
        source,
        re.IGNORECASE,
    )
    if title_labeled:
        _set_field(data, "code_titre_ce", title_labeled.group(1), force=True)
        _set_field(data, "numero_titre_ce", title_labeled.group(2), force=True)
    else:
        title_match = re.search(r"\b22\D{0,30}(\d{6,8})\b", source)
        if title_match:
            _set_field(data, "code_titre_ce", "22", force=True)
            _set_field(data, "numero_titre_ce", title_match.group(1), force=True)
    if not data.get("code_titre_ce") or not data.get("numero_titre_ce"):
        tc, tn = extract_titre_ce_pair(source)
        if tc and tn:
            _set_field(data, "code_titre_ce", tc, force=True)
            _set_field(data, "numero_titre_ce", tn, force=True)
