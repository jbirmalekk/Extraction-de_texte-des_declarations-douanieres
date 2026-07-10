"""Field-level confidence scoring and candidate resolver helpers."""

from __future__ import annotations

import re
from typing import Any, TypedDict

from app.config import settings
from app.services.parser_rules.customs_helpers import _looks_like_garbled_party_name


class FieldOcrProfileDict(TypedDict, total=False):
    """Per-field OCR routing (Architecture B: primary + fallbacks + business gate)."""

    primary: str  # tesseract | paddle | ppstructure
    fallbacks: tuple[str, ...]
    validation_kind: str | None
    psm: int | None
    profile: str | None  # preprocess profile for Tesseract / normalize (numeric, block, general)


CRITICAL_FIELDS = (
    "numero_declaration",
    "date_declaration",
    "type_declaration",
    "importateur_nom",
    "poids_brut",
    "poids_net",
    "code_gdt",
    "montant_liquidation",
    "cle_authentification",
)

FORBIDDEN_CANDIDATE_TOKENS = re.compile(
    r"\b(?:DECLARANT|D[ÉE]CLARANT|CLARANT|CODE|N[°O]|NUMERO|REPERTOIRE|PERTOIRE|CREDIT|N\s*CREDIT)\b",
    re.IGNORECASE,
)
SOURCE_PRIORITY = {"parsed": 0.55, "template": 0.70, "dynamic": 0.75}

# Architecture B — moteur primaire par zone DUM + type de validation métier.
# Les fallbacks ne s'exécutent que si le résultat primaire est vide, faible confiance (si critical), ou invalide métier.
FIELD_OCR_PROFILES: dict[str, FieldOcrProfileDict] = {
    "numero_declaration": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "declaration_id", "psm": 7, "profile": "numeric"},
    "date_declaration": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "date_tn", "psm": 7, "profile": "numeric"},
    "type_declaration": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "type_declaration", "psm": 7, "profile": "numeric"},
    "nbre_articles": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "small_int", "psm": 7, "profile": "numeric"},
    "nombre_colis": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "colis", "psm": 7, "profile": "numeric"},
    "exportateur_code": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "alnum_code", "psm": 7, "profile": "code"},
    "declarant_code": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "declarant_code", "psm": 7, "profile": "numeric"},
    "num_repertoire": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "repertoire", "psm": 7, "profile": "numeric"},
    "bureau_frontiere": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "small_int", "psm": 7, "profile": "numeric"},
    "destination": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "small_int", "psm": 7, "profile": "numeric"},
    "poids_brut": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "weight", "psm": 7, "profile": "numeric"},
    "poids_net": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "weight", "psm": 7, "profile": "numeric"},
    "qualite_fiscale": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "non_empty", "psm": 7, "profile": "numeric"},
    "code_regime_financier": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "regime_delai", "psm": 7, "profile": "numeric"},
    "code_delai": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "regime_delai", "psm": 7, "profile": "numeric"},
    "regime": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "regime_delai", "psm": 7, "profile": "numeric"},
    "valeur_fob": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "amount", "psm": 7, "profile": "numeric"},
    "douane": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "amount", "psm": 7, "profile": "numeric"},
    "coefficient_ajustement": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "amount", "psm": 7, "profile": "numeric"},
    "exportateur_area": {"primary": "paddle", "fallbacks": ("tesseract",), "validation_kind": "name_block", "psm": 6, "profile": None},
    "exportateur_nom": {"primary": "paddle", "fallbacks": ("tesseract",), "validation_kind": "name_block", "psm": 6, "profile": None},
    "adresse_exportateur": {"primary": "paddle", "fallbacks": ("tesseract",), "validation_kind": "address_block", "psm": 7, "profile": None},
    "importateur_nom": {"primary": "paddle", "fallbacks": ("tesseract",), "validation_kind": "name_block", "psm": 6, "profile": None},
    "code_importateur": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "alnum_code", "psm": 7, "profile": "code"},
    "engagement_date": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "date_tn", "psm": 7, "profile": "numeric"},
    "adresse_importateur": {"primary": "paddle", "fallbacks": ("tesseract",), "validation_kind": "address_block", "psm": 6, "profile": None},
    "adresse_entreposage": {"primary": "paddle", "fallbacks": ("tesseract",), "validation_kind": "address_block", "psm": 6, "profile": None},
    "declarant_nom": {"primary": "paddle", "fallbacks": ("tesseract",), "validation_kind": "name_block", "psm": 7, "profile": None},
    "adresse_declarant": {"primary": "paddle", "fallbacks": ("tesseract",), "validation_kind": "address_block", "psm": 6, "profile": None},
    "pays_provenance": {"primary": "paddle", "fallbacks": ("tesseract",), "validation_kind": "country", "psm": 6, "profile": None},
    "pays_achat": {"primary": "paddle", "fallbacks": ("tesseract",), "validation_kind": "country", "psm": 6, "profile": None},
    "pays_premiere_destination": {"primary": "paddle", "fallbacks": ("tesseract",), "validation_kind": "country", "psm": 6, "profile": None},
    "pays_destination_finale": {"primary": "paddle", "fallbacks": ("tesseract",), "validation_kind": "country", "psm": 6, "profile": None},
    "block_transport": {"primary": "ppstructure", "fallbacks": ("paddle", "tesseract"), "validation_kind": "block_text", "psm": 6, "profile": "block"},
    "block_conditions": {"primary": "ppstructure", "fallbacks": ("paddle", "tesseract"), "validation_kind": "block_text", "psm": 6, "profile": "block"},
    "block_finances": {"primary": "ppstructure", "fallbacks": ("paddle", "tesseract"), "validation_kind": "block_text", "psm": 6, "profile": "block"},
    "block_article_1": {"primary": "ppstructure", "fallbacks": ("paddle", "tesseract"), "validation_kind": "block_text", "psm": 6, "profile": "block"},
    "block_liquidation": {"primary": "ppstructure", "fallbacks": ("paddle", "tesseract"), "validation_kind": "block_text", "psm": 6, "profile": "block"},
    "code_titre_ce_cell": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "non_empty", "psm": 7, "profile": "numeric"},
    "numero_titre_ce_cell": {"primary": "tesseract", "fallbacks": ("paddle",), "validation_kind": "non_empty", "psm": 7, "profile": "numeric"},
}


def _infer_ocr_profile_name(field_name: str | None, psm: int) -> str:
    name = str(field_name or "").lower()
    if any(k in name for k in ("code", "numero", "num_", "repertoire", "colis", "gdt", "qcs", "delai", "regime", "poids", "nbre_", "destination", "bureau_frontiere")):
        return "numeric"
    if psm in {7, 8}:
        return "short_text"
    if name.startswith("block_"):
        return "block"
    return "general"


def _default_validation_for_field(field_key: str, inferred: str) -> str | None:
    fk = field_key.lower()
    if inferred == "numeric":
        if "date" in fk:
            return "date_tn"
        if fk == "numero_declaration":
            return "declaration_id"
        if "colis" in fk:
            return "colis"
        if "repertoire" in fk:
            return "repertoire"
        if "poids" in fk:
            return "weight"
        if "regime" in fk or "delai" in fk:
            return "regime_delai"
        return "non_empty"
    if inferred == "block":
        return "block_text"
    if fk.startswith("pays_"):
        return "country"
    if any(x in fk for x in ("adresse", "address")):
        return "address_block"
    if any(x in fk for x in ("nom", "importateur", "exportateur", "declarant")):
        return "name_block"
    return "non_empty"


def get_field_ocr_profile(field_name: str | None, default_psm: int) -> FieldOcrProfileDict:
    """Profil OCR Architecture B (primary + fallbacks + validation)."""
    if field_name and str(field_name).strip():
        key = str(field_name).strip().lower()
        if key in FIELD_OCR_PROFILES:
            base = dict(FIELD_OCR_PROFILES[key])
            if base.get("psm") is None:
                base["psm"] = default_psm
            return base  # type: ignore[return-value]

    inferred = _infer_ocr_profile_name(field_name, default_psm)
    primary = (settings.OCR_ENGINE_PRIMARY or "paddle").lower().strip()
    if primary not in {"paddle", "tesseract", "hybrid"}:
        primary = "paddle"

    if inferred == "numeric":
        prof: FieldOcrProfileDict = {
            "primary": "tesseract",
            "fallbacks": ("paddle",),
            "validation_kind": _default_validation_for_field(str(field_name or ""), inferred),
            "psm": default_psm,
            "profile": "numeric",
        }
        return prof
    if inferred == "block":
        prof = {
            "primary": "ppstructure",
            "fallbacks": ("paddle", "tesseract"),
            "validation_kind": "block_text",
            "psm": default_psm,
            "profile": "block",
        }
        return prof

    if primary == "tesseract":
        fb: tuple[str, ...] = ("paddle",)
    elif primary == "paddle":
        fb = ("tesseract",)
    else:
        fb = ("tesseract", "paddle")

    return {
        "primary": "paddle" if primary == "hybrid" else primary,
        "fallbacks": ("tesseract", "paddle") if primary == "hybrid" else fb,
        "validation_kind": _default_validation_for_field(str(field_name or ""), inferred),
        "psm": default_psm,
        "profile": inferred if inferred in {"numeric", "block"} else None,
    }


def business_validates_ocr(kind: str | None, field_key: str, text: str) -> bool:
    """Garde-fou métier post-OCR (indépendant de la confiance moteur)."""
    raw = "" if text is None else str(text).strip()
    if not raw:
        return False
    if not kind or kind == "non_empty":
        return True

    if kind == "declaration_id":
        return bool(re.fullmatch(r"\d{6}", raw))
    if kind == "date_tn":
        return bool(re.search(r"\b\d{2}[-/.]\d{2}[-/.]\d{4}\b", raw))
    if kind == "type_declaration":
        return bool(re.fullmatch(r"(?:EA|SE|EE|DUM|IM\d*|EX\d*|T1)", raw.upper().replace(" ", "")))
    if kind == "small_int":
        return bool(re.fullmatch(r"\d{1,5}", raw))
    if kind == "colis":
        return bool(re.fullmatch(r"\d{1,3}", raw)) and int(raw) > 0
    if kind == "repertoire":
        return bool(re.fullmatch(r"\d{4,6}", raw))
    if kind == "declarant_code":
        return bool(re.fullmatch(r"\d{2,5}", raw)) and 10 <= int(raw) <= 99999
    if kind == "regime_delai":
        return bool(re.fullmatch(r"\d{1,2}", raw))
    if kind == "weight":
        return bool(re.fullmatch(r"\d+(?:[.,]\d+)?", raw))
    if kind == "amount":
        return bool(re.fullmatch(r"\d+(?:[.,]\d+)?", raw))
    if kind == "alnum_code":
        return len(re.sub(r"[^A-Za-z0-9]", "", raw)) >= 2

    if kind == "name_block":
        fk = (field_key or "").lower()
        if fk in {"importateur_nom", "declarant_nom", "exportateur_nom", "importateur", "declarant", "nom_declarant"}:
            return is_coherent_value(field_key or "importateur_nom", raw)
        alpha = len(re.sub(r"[^A-Za-z]", "", raw))
        return alpha >= 5 and not FORBIDDEN_CANDIDATE_TOKENS.search(raw)

    if kind == "address_block":
        if field_key and is_coherent_value(field_key, raw):
            return True
        compact = len(re.sub(r"[^A-Za-z0-9]", "", raw))
        return compact >= 8 and not FORBIDDEN_CANDIDATE_TOKENS.search(raw)

    if kind == "country":
        return is_coherent_value(field_key if field_key else "pays_provenance", raw)

    if kind == "block_text":
        return len(raw) >= 10

    return True


def composite_ocr_score(*, confidence: float, business_valid: bool) -> float:
    """Score pour choisir le meilleur candidat parmi plusieurs moteurs (Architecture B)."""
    conf = max(0.0, min(1.0, float(confidence)))
    return round((1.45 if business_valid else 0.0) + conf, 4)


def _parse_numeric_coherence(value: Any) -> float | None:
    """Parse un nombre pour règles de cohérence (poids, colis, etc.)."""
    if value is None:
        return None
    s = str(value).strip().replace(" ", "").replace(",", ".")
    s = re.sub(r"[^\d.\-]", "", s)
    if not s or s in {"-", ".", "-.", ".-"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def apply_document_coherence(parsed: dict[str, Any]) -> None:
    """
    Cohérences croisées après agrégation des champs (mutates parsed).
    Ex.: poids brut doit être >= poids net si les deux sont numériques.
    """
    if not isinstance(parsed, dict):
        return

    warns: list[dict[str, Any]] = list(parsed.get("coherence_warnings") or [])
    reasons = set(parsed.get("field_reject_reasons") or [])
    flags = set(parsed.get("flags_validation") or [])

    pb = _parse_numeric_coherence(parsed.get("poids_brut"))
    pn = _parse_numeric_coherence(parsed.get("poids_net"))
    if pb is not None and pn is not None and pb + 1e-6 < pn:
        warns.append({"rule": "poids_brut_lt_poids_net", "poids_brut": pb, "poids_net": pn})
        reasons.add("poids_cross_field_inconsistent")
        flags.add("cross_field_weight_inconsistency")

    nb = _parse_numeric_coherence(parsed.get("nombre_colis"))
    na = _parse_numeric_coherence(parsed.get("nbre_articles"))
    if nb is not None and na is not None and nb > 0 and na > 0 and nb > na * 50:
        warns.append({"rule": "colis_vs_nb_articles_suspicious", "nombre_colis": int(nb), "nbre_articles": int(na)})
        reasons.add("colis_articles_ratio_suspicious")
        flags.add("cross_field_logistics_suspicious")

    if warns:
        parsed["coherence_warnings"] = warns
    parsed["field_reject_reasons"] = sorted(reasons)
    parsed["flags_validation"] = sorted(flags)


def _score_field(field_key: str, value: Any) -> int:
    text = "" if value is None else str(value).strip()
    if not text:
        return 0

    if field_key == "numero_declaration":
        return 95 if re.fullmatch(r"\d{6}", text) else 35
    if field_key == "date_declaration":
        return 90 if re.fullmatch(r"\d{2}[-/.]\d{2}[-/.]\d{4}", text) else 45
    if field_key == "type_declaration":
        return 88 if re.fullmatch(r"(EA|SE|EE|DUM|IM\d*|EX\d*|T1)", text.upper()) else 40
    if field_key == "cle_authentification":
        up = text.upper()
        if re.fullmatch(r"D\d{2,6}[A-Z]{2,4}\d[A-Z]", up):
            return 92
        if re.search(r"D\d{4}[A-Z]{2,4}\d[A-Z]\s*/\s*\d{6,12}", up):
            return 92
        return 35
    if field_key in {"poids_brut", "poids_net", "montant_liquidation", "valeur_fob", "douane"}:
        return 80 if re.fullmatch(r"\d+(?:[.,]\d+)?", text) else 50
    if field_key == "regime":
        return 85 if re.fullmatch(r"\d{1,2}", text) else 40
    if field_key == "coefficient_ajustement":
        return 78 if re.fullmatch(r"\d+(?:[.,]\d+)?", text) else 45
    if field_key in {"importateur_nom", "exportateur_nom", "declarant_nom"}:
        alpha_len = len(re.sub(r"[^A-Za-z]", "", text))
        base = 78 if alpha_len >= 6 else 45
        if field_key == "exportateur_nom" and _looks_like_garbled_party_name(text, role="export"):
            return 22
        if field_key == "importateur_nom" and _looks_like_garbled_party_name(text, role="import"):
            return 22
        return base
    return 65


def build_field_confidences(parsed: dict[str, Any]) -> dict[str, int]:
    return {field: _score_field(field, parsed.get(field)) for field in CRITICAL_FIELDS}


def is_weak_candidate(key: str, value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    if key in {"importateur_nom", "importateur", "exportateur_nom", "declarant_nom", "declarant", "nom_declarant"} and FORBIDDEN_CANDIDATE_TOKENS.search(text):
        return True
    if key in {"exportateur_nom", "exportateur"} and _looks_like_garbled_party_name(text, role="export"):
        return True
    if key in {"importateur_nom", "importateur"} and _looks_like_garbled_party_name(text, role="import"):
        return True
    if key == "exportateur_nom" and (
        re.search(
            r"\b(?:IMPORTATEUR|NESTAHL|NEASTAHL|1113819|STAHL\s+CTS|CERTIFICAT|BECLARATION|NADL)\b",
            text,
            re.IGNORECASE,
        )
        or len(text) > 100
    ):
        return True
    if key in {"declarant_nom", "declarant", "nom_declarant"} and re.search(r"\bTRANSPORT\b", text, re.IGNORECASE):
        return True
    if key == "adresse_exportateur" and re.search(
        r"\b(?:RHINE|STAHL|CTS|RHINESTAUL)\b",
        text,
        re.IGNORECASE,
    ) and not re.search(r"\b(?:JAWDET|SOUKRA|113)\b", text, re.IGNORECASE):
        return True
    if key == "num_repertoire" and not re.fullmatch(r"\d{4,6}", text):
        return True
    if key == "declarant_code" and not re.fullmatch(r"\d{2,5}", text):
        return True
    if key == "nombre_colis" and not re.fullmatch(r"\d{1,3}", text):
        return True
    return False


def is_coherent_value(key: str, value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if key == "nombre_colis":
        return bool(re.fullmatch(r"\d{1,3}", text)) and int(text) > 0
    if key in {"importateur_nom", "importateur", "exportateur_nom", "declarant_nom", "declarant", "nom_declarant"}:
        if key in {"exportateur_nom", "exportateur"} and _looks_like_garbled_party_name(text, role="export"):
            return False
        if key in {"importateur_nom", "importateur"} and _looks_like_garbled_party_name(text, role="import"):
            return False
        return len(re.sub(r"[^A-Za-z]", "", text)) >= 5 and not FORBIDDEN_CANDIDATE_TOKENS.search(text)
    if key in {"pays_provenance", "pays_achat", "pays_premiere_destination", "pays_destination_finale", "pays_destination"}:
        return bool(
            re.search(
                r"\b(TN|DE|FR|US|IT|ES|BE|CN|TR|NL|GB|PT|ET|CY|MA|DZ|LY|EG|SD)\b",
                text,
            )
            or re.search(r"\b(?:ETHIOPIE|ETHIOPI|TUNISIE|ALLEMAGNE|FRANCE)\b", text, re.IGNORECASE)
        )
    if key in {"code_regime_financier", "code_delai"}:
        return bool(re.fullmatch(r"\d{1,2}", text))
    return True


def score_candidate(key: str, value: Any, *, source: str, confidence: float | None = None) -> float:
    base = SOURCE_PRIORITY.get(source, 0.5)
    conf = max(0.0, min(1.0, float(confidence if confidence is not None else 0.65)))
    if is_weak_candidate(key, value):
        return base * 0.2
    if is_coherent_value(key, value):
        return round(base + 0.35 * conf, 4)
    return round(base + 0.1 * conf, 4)


def resolve_field_candidates(
    key: str,
    parsed_value: Any,
    template_value: Any,
    *,
    template_confidence: float | None = None,
) -> tuple[Any, str]:
    parsed_score = score_candidate(key, parsed_value, source="parsed", confidence=0.8) if parsed_value else -1.0
    template_score = score_candidate(key, template_value, source="template", confidence=template_confidence) if template_value else -1.0
    if template_score > parsed_score:
        return template_value, "template"
    return parsed_value, "parsed"
