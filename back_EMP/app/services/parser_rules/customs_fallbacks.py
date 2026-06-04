"""Orchestrates template-aware customs extraction passes."""

from __future__ import annotations

from .country_fields import extract_country_fields
from .customs_articles import (
    extract_article_regime_fallbacks,
    extract_customs_articles,
)
from .customs_cleanup import apply_final_customs_cleanup
from .article_value_fields import extract_article_value_fields
from .financial_fields import extract_financial_fields
from .header_fields import extract_header_fields
from .liquidation_fields import extract_liquidation_fields
from .ocr_noise import normalize_ocr_noise
from .parties_fields import extract_parties_fields
from .template_fields import extract_template_text_fields
from .transport_fields import extract_transport_fields


def apply_customs_template_fallbacks(data, text, zones_text=None, article_rows=None):
    raw = normalize_ocr_noise(text or "")
    zone_values = [str(value) for value in (zones_text or {}).values() if isinstance(value, str) and value.strip()]
    source = "\n".join([raw, *zone_values])
    source = source.replace("§", "5")

    extract_template_text_fields(data, zones_text or {})
    extract_header_fields(data, source)
    extract_parties_fields(data, source)
    extract_country_fields(data, source)
    extract_transport_fields(data, source)
    extract_financial_fields(data, source)
    extract_article_value_fields(data, source)
    extract_customs_articles(data, source)
    extract_article_regime_fallbacks(data, source)
    extract_liquidation_fields(data, source)

    if data.get("exportateur_nom") and not data.get("exportateur"):
        data["exportateur"] = data["exportateur_nom"]
    if data.get("importateur_nom") and not data.get("importateur"):
        data["importateur"] = data["importateur_nom"]
    if data.get("declarant_nom") and not data.get("declarant"):
        data["declarant"] = data["declarant_nom"]
    if data.get("nbre_articles") and not data.get("nombre_articles"):
        data["nombre_articles"] = data["nbre_articles"]
    if data.get("valeur_fob") and not data.get("valeur_fob_dt"):
        data["valeur_fob_dt"] = data["valeur_fob"]
    if data.get("douane") and not data.get("valeur_dinars"):
        data["valeur_dinars"] = data["douane"]
    elif data.get("valeur_fob_dt") and not data.get("valeur_dinars"):
        data["valeur_dinars"] = data["valeur_fob_dt"]
    elif data.get("valeur_fob") and not data.get("valeur_dinars"):
        data["valeur_dinars"] = data["valeur_fob"]
    if data.get("code_qcs") and not data.get("qcs"):
        data["qcs"] = data["code_qcs"]
    if data.get("designation_marchandises") and not data.get("description_marchandise"):
        data["description_marchandise"] = data["designation_marchandises"]
    if str(data.get("relation_acheteur_vendeur") or "").strip() in {"0", "08"}:
        data["relation_acheteur_vendeur"] = None

    apply_final_customs_cleanup(data, source)

    return data
