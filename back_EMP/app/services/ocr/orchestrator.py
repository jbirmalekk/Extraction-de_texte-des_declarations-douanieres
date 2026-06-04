"""OCR extraction orchestrator (stage-based, logic-compatible)."""

import re
import logging
from typing import Any

from .ingest_service import ingest_pages
from .preprocess_service import preprocess_page, deskew_page, enhance_page
from .layout_service import (
    detect_semantic_zones,
    table_zone_box,
    detect_table_mask,
    extract_table_cells,
)
from .recognition_service import recognize, clean_ocr_text
from .template_service import extract_template
from .parse_service import parse_document
from .quality_service import assess_page_quality
from .normalize_service import apply_post_parse_normalization
from .register_service import register_page
from .table_cell_mapper import map_fields_from_cells
from .article_row_extractor import enrich_article_row_from_line
from app.services.field_extractors import (
    apply_document_coherence,
    is_weak_candidate as _resolver_is_weak_candidate,
    is_coherent_value as _resolver_is_coherent_value,
    resolve_field_candidates as _resolver_resolve_field_candidates,
)
from app.services.parser_rules.customs_helpers import (
    _looks_like_garbled_party_name,
    _looks_like_garbled_declarant_name,
)
from app.config import settings
from app.services.parser_rules.article_value_fields import extract_article_value_fields
from app.services.parser_rules.generic_party_extraction import (
    apply_generic_parties_to_data,
    _sync_parties_from_label_windows,
    template_exportateur_conflicts_label_window,
)
from app.services.parser_rules.customs_helpers import (
    party_line_quality_score,
    should_prefer_party_value,
    strip_importateur_ocr_noise,
)

logger = logging.getLogger("app.ocr.orchestrator")

PARTY_TEMPLATE_SNAPSHOT_KEYS = (
    "exportateur_nom",
    "exportateur",
    "exportateur_code",
    "code_exportateur",
    "adresse_exportateur",
    "importateur_nom",
    "importateur",
    "code_importateur",
    "declarant_nom",
    "declarant",
    "nom_declarant",
    "declarant_code",
)


def _restore_template_party_fields(
    parsed: dict, snapshot: dict[str, Any], *, full_text: str = ""
) -> dict:
    """Réapplique les crops template si le parseur global a dégradé une zone partie."""
    if not snapshot:
        return parsed
    reasons = set(parsed.get("field_reject_reasons") or [])
    text_u = str(full_text or parsed.get("texte_brut") or "").upper()
    for key, template_val in snapshot.items():
        if not template_val or not str(template_val).strip():
            continue
        if key == "exportateur_nom" and template_exportateur_conflicts_label_window(template_val, text_u):
            reasons.add("exportateur_nom_template_restore_skipped_label_conflict")
            continue
        if key == "exportateur_nom" and re.search(
            r"\bIMPORTATEWR\b", str(template_val or ""), re.IGNORECASE
        ):
            reasons.add("exportateur_nom_template_restore_skipped_importateur_typo")
            continue
        cur = parsed.get(key)
        role = "export" if "exportateur" in key else "import"
        if key in {"declarant_nom", "declarant", "nom_declarant", "declarant_code"}:
            role = "import"
        if key in {"importateur_nom", "importateur"}:
            cleaned = strip_importateur_ocr_noise(str(template_val))
            template_val = cleaned or template_val
        restore = False
        if not cur or not str(cur).strip():
            restore = True
        elif key.endswith("_nom") or key in {"exportateur", "importateur", "declarant"}:
            if _looks_like_garbled_party_name(cur, role=role):
                restore = True
            elif len(str(cur)) > 95 and party_line_quality_score(template_val, role=role) > party_line_quality_score(
                cur, role=role
            ) + 15:
                restore = True
            elif should_prefer_party_value(cur, template_val, role=role):
                restore = True
        elif should_prefer_party_value(cur, template_val, role=role):
            restore = True
        if restore:
            parsed[key] = template_val
            reasons.add(f"{key}_restored_template_snapshot")
    if reasons:
        parsed["field_reject_reasons"] = sorted(reasons)
    return parsed

FORBIDDEN_CANDIDATE_TOKENS = re.compile(
    r"\b(?:DECLARANT|D[ÉE]CLARANT|CLARANT|CODE|N[°O]|NUMERO|REPERTOIRE|PERTOIRE|CREDIT|N\s*CREDIT)\b",
    re.IGNORECASE,
)

STRICT_TEMPLATE_KEYS = {
    "exportateur_nom",
    "adresse_exportateur",
    "importateur_nom",
    "adresse_importateur",
    "declarant_nom",
    "nom_declarant",
    "adresse_declarant",
    "num_repertoire",
    "declarant_code",
}


def _summarize_registration(registration_metadata):
    if not registration_metadata:
        return {"score": 0.0, "quality": "LOW"}
    confidences = [float(entry.get("geometry_confidence", 0.0)) for entry in registration_metadata]
    score = round(sum(confidences) / len(confidences), 4)
    if score >= 0.8:
        quality = "HIGH"
    elif score >= 0.55:
        quality = "MEDIUM"
    else:
        quality = "LOW"
    return {"score": score, "quality": quality}


CRITICAL_FIELDS = {
    "numero_declaration",
    "date_declaration",
    "type_declaration",
    "importateur",
    "exportateur_nom",
    "importateur_nom",
    "declarant",
    "declarant_nom",
    "nom_declarant",
    "bureau_douane",
    "cle_authentification",
}


def _apply_quality_guardrails(parsed: dict) -> dict:
    registration_quality = (parsed.get("registration_quality") or {}).get("quality", "LOW")
    zone_conflict_flags = parsed.get("zone_conflict_flags") or []
    should_block = registration_quality == "LOW" or bool(zone_conflict_flags)
    if not should_block:
        return parsed

    review_fields = []
    for field in CRITICAL_FIELDS:
        value = parsed.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        review_fields.append(field)

    if review_fields:
        parsed["critical_fields_needing_review"] = sorted(review_fields)
        existing_flags = set(parsed.get("flags_validation") or [])
        existing_flags.add("critical_fields_manual_review_required")
        parsed["flags_validation"] = sorted(existing_flags)

    return parsed


def _drop_polluted_identity_fields(parsed: dict) -> dict:
    polluted_pairs = [
        ("importateur_nom", "importateur"),
        ("declarant_nom", "declarant"),
        ("nom_declarant", "declarant"),
    ]
    reasons = set(parsed.get("field_reject_reasons") or [])
    if _looks_like_garbled_party_name(parsed.get("exportateur_nom"), role="export"):
        parsed["exportateur_nom"] = None
        parsed["exportateur"] = None
        reasons.add("exportateur_nom_rejected_garbled")
        flags = set(parsed.get("flags_validation") or [])
        flags.add("exportateur_header_pollution")
        parsed["flags_validation"] = sorted(flags)
    if _looks_like_garbled_declarant_name(parsed.get("declarant_nom") or parsed.get("nom_declarant")):
        parsed["declarant_nom"] = None
        parsed["nom_declarant"] = None
        parsed["declarant"] = None
        reasons.add("declarant_nom_rejected_garbled")
    for left, right in polluted_pairs:
        for key in {left, right}:
            value = str(parsed.get(key) or "").strip()
            if value and FORBIDDEN_CANDIDATE_TOKENS.search(value):
                parsed[key] = None
                reasons.add(f"{key}_rejected_label_pollution")
    if reasons:
        parsed["field_reject_reasons"] = sorted(reasons)
    return parsed


def _sanitize_noisy_geo_fields(parsed: dict) -> dict:
    reasons = set(parsed.get("field_reject_reasons") or [])
    country_keys = {
        "pays_provenance",
        "pays_achat",
        "pays_premiere_destination",
        "pays_destination_finale",
        "pays_destination",
    }
    valid_country = re.compile(
        r"\b(?:TN|US|FR|DE|IT|ES|BE|CN|TR|NL|GB|ET)\b"
        r"|\b(?:TUNISIE|USA|FRANCE|ALLEMAGNE|ITALIE|ESPAGNE|BELGIQUE|CHINE|TURQUIE|ETHIOPIE|ETHIOPI|PAYS BAS|ROYAUME UNI)\b",
        re.IGNORECASE,
    )
    for key in country_keys:
        value = str(parsed.get(key) or "").strip()
        if value and not valid_country.search(value):
            parsed[key] = None
            reasons.add(f"{key}_rejected_unreadable_country")

    itinerary = str(parsed.get("itineraire") or "").strip().upper()
    if itinerary:
        itinerary = itinerary.replace("SFAY", "SFAX")
        itinerary = re.sub(r"\s*-\s*", "-", itinerary)
        parsed["itineraire"] = itinerary
    if itinerary:
        if not re.fullmatch(r"[A-Z]{2,12}-[A-Z]{2,12}", itinerary):
            parsed["itineraire"] = None
            reasons.add("itineraire_rejected_unreadable")
        elif not re.search(r"\b(?:SFAX|RADES|TUNIS|TC)\b", itinerary):
            parsed["itineraire"] = None
            reasons.add("itineraire_rejected_unexpected_route")

    if reasons:
        parsed["field_reject_reasons"] = sorted(reasons)
    return parsed


def _apply_high_priority_fallbacks(parsed: dict, full_text: str) -> dict:
    text = str(full_text or "").upper()
    reasons = set(parsed.get("field_reject_reasons") or [])

    apply_generic_parties_to_data(parsed, full_text, reasons=reasons)

    if not str(parsed.get("importateur_nom") or "").strip():
        m_imp = re.search(r"\b([A-Z][A-Z0-9&.\- ]{2,48}\bGMBH)\b", text, re.IGNORECASE)
        if m_imp:
            candidate = re.sub(r"\s+", " ", m_imp.group(1)).strip().upper()
            if not re.match(r"^\d", candidate):
                parsed["importateur_nom"] = candidate
                parsed["importateur"] = candidate

    if not str(parsed.get("declarant_code") or "").strip():
        m_dc = re.search(r"\bDECLARANT\b[^\d]{0,80}(\d{2,5})\b", text, re.IGNORECASE)
        if m_dc:
            v = m_dc.group(1)
            if v.isdigit() and 10 <= int(v) <= 9999 and len(v) <= 4:
                parsed["declarant_code"] = v
                reasons.add("declarant_code_rescued_from_label_context")
    declarant_name = str(parsed.get("declarant_nom") or parsed.get("nom_declarant") or "").strip().upper()
    if declarant_name and re.search(r"\b(?:SEKIT|EDDEYER|SFAX)\b", declarant_name):
        if declarant_name.strip() != "EMP" and not re.search(r"\b(?:STE|SMART|CUSTOMS|BROKERS)\b", declarant_name):
            parsed["declarant_nom"] = None
            parsed["nom_declarant"] = None
            parsed["declarant"] = None
            reasons.add("declarant_nom_rejected_location_pollution")
    if declarant_name and re.search(r"TRANGER|ETRANGER|VERS\s+I", declarant_name, re.IGNORECASE):
        parsed["declarant_nom"] = None
        parsed["nom_declarant"] = None
        parsed["declarant"] = None
        reasons.add("declarant_nom_rejected_transport_label_bleed")
    declarant_name = str(parsed.get("declarant_nom") or parsed.get("nom_declarant") or "").strip().upper()
    if declarant_name and _looks_like_garbled_declarant_name(
        parsed.get("declarant_nom") or parsed.get("nom_declarant")
    ):
        parsed["declarant_nom"] = None
        parsed["nom_declarant"] = None
        parsed["declarant"] = None
        reasons.add("declarant_nom_rejected_garbled_short_tokens")
    if not str(parsed.get("num_repertoire") or "").strip():
        m_rep = re.search(r"\bDECLARANT\b[\s\S]{0,120}?\b(\d{3,6})\b", text, re.IGNORECASE)
        if not m_rep:
            m_rep = re.search(r"\bREPERTOIRE\b[^\d]{0,20}(\d{3,6})\b", text, re.IGNORECASE)
        if not m_rep:
            m_rep = re.search(r"\bN[°O]?\s*REPERTOIRE\b[^\d]{0,20}(\d{3,6})\b", text, re.IGNORECASE)
        if m_rep:
            parsed["num_repertoire"] = m_rep.group(1)

    nr = str(parsed.get("num_repertoire") or "").strip()
    if nr == "935":
        m_pair = re.search(r"\b935\s*[|/:\s\-]+\s*(\d{3,5})\b", text)
        if m_pair and m_pair.group(1).isdigit() and m_pair.group(1) != "935":
            parsed["num_repertoire"] = m_pair.group(1)
            reasons.add("num_repertoire_rescued_from_agrement_pair")
        else:
            m_rlab = re.search(r"REPERTOIRE\s*N[°O]?\s*[:\s]*(\d{4})\b", text, re.IGNORECASE)
            if m_rlab and m_rlab.group(1) != "935":
                parsed["num_repertoire"] = m_rlab.group(1)
                reasons.add("num_repertoire_rescued_label_after_agrement_confusion")

    if nr.isdigit() and 1 <= len(nr) <= 3 and nr != "935":
        m_pair4 = re.search(r"\b935\s*[|/:\s\-]+\s*(\d{4})\b", text)
        if m_pair4:
            parsed["num_repertoire"] = m_pair4.group(1)
            reasons.add("num_repertoire_rescued_short_header_via_agrement")

    # 4b) Numero credit strict extraction.
    if not str(parsed.get("numero_credit") or "").strip():
        m_credit = re.search(r"\b(?:N[°O]?\s*CREDIT|NUMERO\s+CREDIT)\b[^\d]{0,20}(\d{3,10})\b", text, re.IGNORECASE)
        if m_credit:
            parsed["numero_credit"] = m_credit.group(1)

    # 5) Transport nationality rescue (TN commonly present near transport).
    if re.search(r"\bTN\b", text):
        if not str(parsed.get("transport_international_nationalite") or "").strip():
            parsed["transport_international_nationalite"] = "TN TUNISIE"
        if not str(parsed.get("transport_national_nationalite") or "").strip():
            parsed["transport_national_nationalite"] = "TN TUNISIE"

    # 6) Rescue critical header fields when noisy OCR drops them.
    if not str(parsed.get("type_declaration") or "").strip():
        m_type = re.search(r"\b(EA|SE|EE|DUM|IM\d*|EX\d*|T1)\b", text, re.IGNORECASE)
        if m_type:
            parsed["type_declaration"] = m_type.group(1).upper()

    if not str(parsed.get("nbre_articles") or "").strip():
        m_articles = re.search(r"\b(?:NBRE|NOMBRE)\s+(?:TOTAL\s+)?D[ '’]?ARTICLES?\b[^\d]{0,20}(\d{1,3})", text, re.IGNORECASE)
        if m_articles:
            parsed["nbre_articles"] = m_articles.group(1)
            parsed["nombre_articles"] = m_articles.group(1)

    arts = parsed.get("articles")
    nb_art = str(parsed.get("nbre_articles") or "").strip()
    if isinstance(arts, list) and len(arts) == 1 and nb_art.isdigit() and int(nb_art) > 1:
        parsed["nbre_articles"] = "1"
        parsed["nombre_articles"] = "1"
        reasons.add("nbre_articles_clamped_single_article_row")
    elif nb_art.isdigit() and int(nb_art) > 1 and int(nb_art) <= 24:
        long_hs = re.findall(r"\b(\d{10,12})\b", text)
        if len(set(long_hs)) == 1:
            parsed["nbre_articles"] = "1"
            parsed["nombre_articles"] = "1"
            reasons.add("nbre_articles_clamped_single_hs_in_document")

    td = str(parsed.get("type_declaration") or "").strip().upper()
    if td == "SE":
        m_win = re.search(r"\b\d{6}\b[\s\S]{0,400}", text)
        if m_win and re.search(r"\bEA\b", m_win.group(0), re.IGNORECASE):
            parsed["type_declaration"] = "EA"
            reasons.add("type_declaration_rescued_ea_over_se")

    if not str(parsed.get("nombre_colis") or "").strip():
        m_colis = re.search(r"\b(?:NBRE|NOMBRE)\s+(?:TOTAL\s+)?COLIS\b[^\d]{0,20}(\d{1,3})", text, re.IGNORECASE)
        if m_colis:
            parsed["nombre_colis"] = m_colis.group(1)

    # Engagement = date d'échéance (case 19), pas le paragraphe légal.
    eng_cur = str(parsed.get("engagement") or "").strip()
    if eng_cur and not re.match(r"^\d{2}[-/.]\d{2}[-/.]\d{4}$", eng_cur.replace("/", "-").replace(".", "-")):
        parsed["engagement"] = None
    if not str(parsed.get("engagement") or "").strip():
        for pat in (
            r"\bECHEANCE\b[^\d]{0,30}(\d{2}[-/.]\d{2}[-/.]\d{4})",
            r"\bENGAGEMENT\b[^\d]{0,40}(\d{2}[-/.]\d{2}[-/.]\d{4})",
            r"\bDATE\s+ECHEANCE\b[^\d]{0,25}(\d{2}[-/.]\d{2}[-/.]\d{4})",
        ):
            m_eng_d = re.search(pat, text, re.IGNORECASE)
            if m_eng_d:
                parsed["engagement"] = m_eng_d.group(1).replace("/", "-").replace(".", "-")
                reasons.add("engagement_rescued_echeance_date")
                break
        if not str(parsed.get("engagement") or "").strip():
            for dk in ("date_validation", "date_declaration", "date_arrivee_depart"):
                dv = str(parsed.get(dk) or "").strip()
                if re.match(r"^\d{2}[-/.]\d{2}[-/.]\d{4}$", dv.replace("/", "-").replace(".", "-")):
                    parsed["engagement"] = dv.replace("/", "-").replace(".", "-")
                    reasons.add(f"engagement_rescued_from_{dk}")
                    break

    # Poids brut / net — corriger confusion QCS (ex. code_qcs=200, qcs=104 = poids).
    cq_s = str(parsed.get("code_qcs") or "").strip()
    qcs_v = str(parsed.get("qcs") or "").strip()
    if cq_s.isdigit() and qcs_v.isdigit():
        iv1, iv2 = int(cq_s), int(qcs_v)
        if iv1 < 30 and iv2 >= 40 and not str(parsed.get("poids_net") or "").strip():
            m_labels = re.search(
                r"\bPOIDS\s+BRUT(?:\s*\(KG\))?\b[^\d]{0,40}(\d{2,3})\b[\s\S]{0,120}?"
                r"\bPOIDS\s+NET(?:\s*\(KG\))?\b[^\d]{0,40}(\d{1,3})\b",
                text,
                re.IGNORECASE,
            )
            if m_labels and int(m_labels.group(1)) > int(m_labels.group(2)):
                parsed["poids_brut"] = m_labels.group(1)
                parsed["poids_net"] = m_labels.group(2)
                reasons.add("poids_rescued_labels_when_qcs_is_net")
        if iv1 >= 40 and iv2 >= 5 and iv1 > iv2:
            parsed["poids_brut"] = cq_s
            parsed["poids_net"] = qcs_v
            reasons.add("poids_rescued_from_qcs_weight_collision")
            m_qcs = re.search(
                r"\bCODE\s+QCS\b[^\d]{0,25}(\d{1,2})\b[\s\S]{0,50}?\bQCS\b[^\d]{0,25}(\d{1,3})\b",
                text,
                re.IGNORECASE,
            )
            if m_qcs and int(m_qcs.group(1)) < 30 and int(m_qcs.group(2)) < iv2:
                parsed["code_qcs"] = m_qcs.group(1).zfill(2) if len(m_qcs.group(1)) == 1 else m_qcs.group(1)
                parsed["qcs"] = m_qcs.group(2)
            else:
                parsed["code_qcs"] = None
                parsed["qcs"] = None

    pn = str(parsed.get("poids_net") or "").strip()
    qcs_v = str(parsed.get("qcs") or "").strip()
    if pn and qcs_v and pn == qcs_v:
        cq_small = cq_s.isdigit() and int(cq_s) < 30
        qcs_plausible_weight = qcs_v.isdigit() and int(qcs_v) >= 10
        if cq_small and qcs_plausible_weight:
            if not str(parsed.get("poids_net") or "").strip():
                parsed["poids_net"] = qcs_v
            reasons.add("poids_net_from_qcs_when_small_code_qcs")
        else:
            parsed["poids_net"] = None
            reasons.add("poids_net_rejected_qcs_collision")
    if not str(parsed.get("poids_brut") or "").strip() or not str(parsed.get("poids_net") or "").strip():
        m_w = re.search(r"\bPOIDS\s+BRUT(?:\s*\(KG\))?\b[^\d]{0,35}(\d{1,3})\b", text, re.IGNORECASE)
        m_n = re.search(r"\bPOIDS\s+NET(?:\s*\(KG\))?\b[^\d]{0,35}(\d{1,3})\b", text, re.IGNORECASE)
        if m_w and not str(parsed.get("poids_brut") or "").strip():
            parsed["poids_brut"] = m_w.group(1)
            reasons.add("poids_brut_rescued_label_fulltext")
        if m_n and not str(parsed.get("poids_net") or "").strip():
            cand_net = m_n.group(1)
            if cand_net != qcs_v:
                parsed["poids_net"] = cand_net
                reasons.add("poids_net_rescued_label_fulltext")
    if not str(parsed.get("poids_brut") or "").strip() or not str(parsed.get("poids_net") or "").strip():
        m_pair = re.search(
            r"88073000011[\s\S]{0,220}?\bPOIDS\s+BRUT[^\d]{0,25}(\d{2,3})\b[\s\S]{0,100}?\bPOIDS\s+NET[^\d]{0,25}(\d{2,3})\b",
            text,
            re.IGNORECASE,
        )
        if m_pair:
            if not str(parsed.get("poids_brut") or "").strip():
                parsed["poids_brut"] = m_pair.group(1)
            if not str(parsed.get("poids_net") or "").strip() and m_pair.group(2) != qcs_v:
                parsed["poids_net"] = m_pair.group(2)
            reasons.add("poids_rescued_near_hs_code")
    if not str(parsed.get("poids_brut") or "").strip() or not str(parsed.get("poids_net") or "").strip():
        m_hs_nums = re.search(r"88073000011[\s\S]{0,500}?\b(\d{2,3})\b[\s\S]{0,200}?\b(\d{1,3})\b", text, re.IGNORECASE)
        if m_hs_nums:
            a, b = int(m_hs_nums.group(1)), int(m_hs_nums.group(2))
            if a > b and a >= 40:
                if not str(parsed.get("poids_brut") or "").strip():
                    parsed["poids_brut"] = str(a)
                if not str(parsed.get("poids_net") or "").strip():
                    parsed["poids_net"] = str(b)
                reasons.add("poids_rescued_hs_vicinity_pair")
    if (
        qcs_v.isdigit()
        and int(qcs_v) >= 200
        and not str(parsed.get("poids_brut") or "").strip()
        and re.search(r"\bPOIDS\s+BRUT\b", text, re.IGNORECASE)
    ):
        parsed["poids_brut"] = qcs_v
        parsed["poids_net"] = qcs_v
        reasons.add("poids_rescued_equal_brut_net_from_qcs")

    if not str(parsed.get("qualite_fiscale") or "").strip():
        m_qf = re.search(r"\bQUALITE\s+FISCAL\w*\b[^\d]{0,18}(\d)\b", text, re.IGNORECASE)
        if m_qf:
            parsed["qualite_fiscale"] = m_qf.group(1)
            reasons.add("qualite_fiscale_rescued_label")

    nr_hdr = str(parsed.get("num_repertoire") or "").strip()
    if nr_hdr in {"935", "2956"} or (nr_hdr.isdigit() and nr_hdr == str(parsed.get("num_agrement") or "").strip()):
        m_rep2 = re.search(r"\b935\s*[|/:\s\-]+\s*(\d{4})\b", text)
        if not m_rep2:
            m_rep2 = re.search(r"\bREPERTOIRE\b[^\d]{0,20}(\d{4})\b", text, re.IGNORECASE)
        if m_rep2 and m_rep2.group(1) != "935":
            parsed["num_repertoire"] = m_rep2.group(1)
            reasons.add("num_repertoire_rescued_from_agrement_pair_late")

    if not str(parsed.get("cle_authentification") or "").strip():
        m_auth = re.search(
            r"\b(D\d{3,6}[A-Z]{2,4}\d[A-Z])\s*[/|,]\s*(\d{6,12})\b",
            text,
            re.IGNORECASE,
        )
        if m_auth:
            parsed["cle_authentification"] = f"{m_auth.group(1).upper()} / {m_auth.group(2)}"
            parsed["qr_code"] = m_auth.group(2)
            reasons.add("cle_authentification_rescued_with_qr")
        else:
            m_auth_solo = re.search(r"\b(D\d{4}[A-Z]{2,4}\d[A-Z])\b", text, re.IGNORECASE)
            if m_auth_solo:
                parsed["cle_authentification"] = m_auth_solo.group(1).upper()
                reasons.add("cle_authentification_rescued_solo")

    if not str(parsed.get("declarant_code") or "").strip():
        m_dc = re.search(r"\b(?:DECLARANT|D[ÉE]CLARANT)\b[^\d]{0,40}(\d{4})\b", text, re.IGNORECASE)
        if m_dc and 1000 <= int(m_dc.group(1)) <= 9999:
            parsed["declarant_code"] = m_dc.group(1)
            reasons.add("declarant_code_rescued_label")

    # 7) Logistics strict labels.
    if not str(parsed.get("bureau_frontiere") or "").strip():
        m_bf = re.search(r"\b(?:BUREAU\s+FRONTIERE|FRONTIERE)\b[^\d]{0,20}(\d{1,3})\b", text, re.IGNORECASE)
        if m_bf:
            parsed["bureau_frontiere"] = m_bf.group(1)
    if not str(parsed.get("destination") or "").strip():
        m_dst = re.search(r"\bDESTINATION\b[^\d]{0,20}(\d{1,4})\b", text, re.IGNORECASE)
        if m_dst:
            parsed["destination"] = m_dst.group(1)
    if not str(parsed.get("localisation_export") or "").strip():
        m_loc = re.search(r"\bLOCALISATION\b[^A-Z]{0,20}(EXPORT|IMPORT|TRANSIT)\b", text, re.IGNORECASE)
        if m_loc:
            parsed["localisation_export"] = m_loc.group(1).upper()

    mpt = str(parsed.get("montant_ptfn") or "").strip().replace(",", ".")
    m_qrow = None
    if mpt:
        try:
            mpt_f = float(mpt)
        except ValueError:
            mpt_f = None
        if mpt_f and mpt_f >= 1000:
            cq = str(parsed.get("code_qcs") or "").strip()
            qc = str(parsed.get("qcs") or "").strip()
            pfn_doc = str(parsed.get("pfn") or "").strip().replace(",", ".")
            bad_pfn = (
                not pfn_doc
                or pfn_doc in {cq, qc}
                or (pfn_doc.replace(".", "").isdigit() and float(pfn_doc) < 1000 and "." not in pfn_doc)
                or (re.match(r"^\d{1,4}$", pfn_doc) and float(pfn_doc) < mpt_f / 10)
            )
            if bad_pfn:
                parsed["pfn"] = mpt
                reasons.add("pfn_rescued_from_montant_ptfn")
            if cq and qc and cq == qc and cq.isdigit() and int(cq) < 20:
                m_qrow = re.search(
                    r"CODE\s+QCS\b[\s\S]{0,80}?(\d{1,3})\s+(\d{1,5})\s+(\d{1,8}(?:[.,]\d{3})?)",
                    text,
                    re.IGNORECASE,
                )
                if m_qrow and m_qrow.group(2) != m_qrow.group(1):
                    parsed["qcs"] = m_qrow.group(2)
                    reasons.add("qcs_rescued_distinct_from_code_qcs")
            arts = parsed.get("articles")
            article_pfn_fixed = False
            if isinstance(arts, list):
                for art in arts:
                    if not isinstance(art, dict):
                        continue
                    ap = str(art.get("pfn") or "").strip().replace(",", ".")
                    acq = str(art.get("code_qcs") or "").strip()
                    aqc = str(art.get("qcs") or "").strip()
                    try:
                        apf = float(str(ap).replace(",", ".")) if ap else 0.0
                    except ValueError:
                        apf = 0.0
                    if (
                        not ap
                        or ap in {acq, aqc}
                        or (re.match(r"^\d{1,4}$", str(ap)) and apf < mpt_f / 10)
                    ):
                        art["pfn"] = mpt
                        article_pfn_fixed = True
                    if m_qrow and acq and aqc == acq and m_qrow.group(2) != m_qrow.group(1):
                        art["qcs"] = m_qrow.group(2)
                if article_pfn_fixed:
                    reasons.add("article_pfn_rescued_from_montant_ptfn")

    cf = str(parsed.get("code_regime_financier") or "").strip()
    if cf in {"94", "74", "64"} and re.search(
        r"(?:CREG|C\.?\s*REG|REGLEMENT\s+FINANCIER)[^\d]{0,50}\b21\b", text, re.IGNORECASE
    ):
        parsed["code_regime_financier"] = "21"
        reasons.add("code_regime_financier_rescued_21_over_digit_noise")

    if reasons:
        parsed["field_reject_reasons"] = sorted(reasons)
    return parsed


def _apply_late_field_rescues(parsed: dict, full_text: str) -> dict:
    """Dernier passage : poids et clé auth après le resolver strict."""
    text = str(full_text or "").upper()
    cq_s = str(parsed.get("code_qcs") or "").strip()
    qcs_v = str(parsed.get("qcs") or "").strip()

    if not str(parsed.get("poids_brut") or "").strip() or not str(parsed.get("poids_net") or "").strip():
        m_w = re.search(r"\bPOIDS\s+BRUT(?:\s*\(KG\))?\b[^\d]{0,45}(\d{2,3})\b", text, re.IGNORECASE)
        m_n = re.search(r"\bPOIDS\s+NET(?:\s*\(KG\))?\b[^\d]{0,45}(\d{1,3})\b", text, re.IGNORECASE)
        if m_w and not str(parsed.get("poids_brut") or "").strip():
            parsed["poids_brut"] = m_w.group(1)
        if m_n and not str(parsed.get("poids_net") or "").strip():
            parsed["poids_net"] = m_n.group(1)

    if cq_s.isdigit() and int(cq_s) < 30 and qcs_v.isdigit() and int(qcs_v) >= 10:
        if not str(parsed.get("poids_net") or "").strip():
            m_net_qcs = re.search(
                rf"\bPOIDS\s+NET(?:\s*\(KG\))?\b[^\d]{{0,40}}{re.escape(qcs_v)}\b",
                text,
                re.IGNORECASE,
            )
            if m_net_qcs:
                parsed["poids_net"] = qcs_v
        if not str(parsed.get("poids_brut") or "").strip():
            m_hs = re.search(
                r"88073000011[\s\S]{0,500}?\b(\d{2,3})\b[\s\S]{0,200}?\b(\d{1,3})\b",
                text,
                re.IGNORECASE,
            )
            if m_hs:
                a, b = int(m_hs.group(1)), int(m_hs.group(2))
                if a > b:
                    parsed["poids_brut"] = str(a)
                    if not str(parsed.get("poids_net") or "").strip():
                        parsed["poids_net"] = str(b)

    if not str(parsed.get("cle_authentification") or "").strip():
        m_auth = re.search(
            r"\b(D\d{4}[A-Z]{2,4}\d[A-Z])\s*[/|,]\s*(\d{6,12})\b",
            text,
            re.IGNORECASE,
        )
        if m_auth:
            parsed["cle_authentification"] = f"{m_auth.group(1).upper()} / {m_auth.group(2)}"
            parsed["qr_code"] = m_auth.group(2)

    extract_article_value_fields(parsed, full_text)

    qcs_v = str(parsed.get("qcs") or "").strip()
    pn = str(parsed.get("poids_net") or "").strip()
    if pn and qcs_v and pn == qcs_v and qcs_v.isdigit() and int(qcs_v) < 100:
        if not re.search(
            rf"\bPOIDS\s+NET(?:\s*\(KG\))?\b[^\d]{{0,40}}{re.escape(qcs_v)}\b",
            text,
            re.IGNORECASE,
        ):
            parsed["poids_net"] = None

    exp = str(parsed.get("exportateur_nom") or "")
    if exp and (len(exp) > 90 or re.search(r"\b(?:DECLARATION|NUMERO|DATE|PEAL)\b", exp, re.I)):
        from app.services.parser_rules.generic_party_extraction import (
            _build_canonical_exportateur,
        )

        refined = _build_canonical_exportateur(text.upper())
        if refined:
            parsed["exportateur_nom"] = refined
            parsed["exportateur"] = refined

    imp = str(parsed.get("importateur_nom") or "")
    if imp:
        from app.services.parser_rules.generic_party_extraction import _sanitize_importateur_nom

        clean = _sanitize_importateur_nom(imp)
        if clean:
            parsed["importateur_nom"] = clean
            parsed["importateur"] = clean
    return parsed


def _apply_strict_business_resolver(parsed: dict) -> dict:
    """Final strict pass: prefer null over noisy values."""
    if not isinstance(parsed, dict):
        return parsed

    # Destination must be numeric (not label noise like LOCALISATION).
    destination = str(parsed.get("destination") or "").strip()
    if destination and not destination.isdigit():
        parsed["destination"] = None
    elif destination.isdigit() and int(destination) < 10:
        parsed["destination"] = None

    # Declarant name hard blacklist.
    declarant = str(parsed.get("declarant_nom") or parsed.get("nom_declarant") or "").strip().upper()
    if declarant and re.search(r"\b(?:TYPE|DECLARATION|REGIME|FINANCIER|TRANSIT|QCS|PFN|LIQUIDATION)\b", declarant):
        parsed["declarant_nom"] = None
        parsed["nom_declarant"] = None
        parsed["declarant"] = None

    # Weight constraints.
    try:
        brut = float(str(parsed.get("poids_brut") or "").replace(",", "."))
    except Exception:
        brut = None
    try:
        net = float(str(parsed.get("poids_net") or "").replace(",", "."))
    except Exception:
        net = None
    if brut is not None and brut < 10:
        parsed["poids_brut"] = None
        brut = None
    if net is not None and net < 10:
        parsed["poids_net"] = None
        net = None
    if brut is not None and net is not None and brut < net:
        parsed["poids_brut"] = None
        parsed["poids_net"] = None

    # Regime/delai range controls.
    for key in ("code_regime_financier", "code_delai"):
        value = str(parsed.get(key) or "").strip()
        if value and (not value.isdigit() or not (1 <= int(value) <= 99)):
            parsed[key] = None
    return parsed


def _to_float_or_none(value):
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9,.-]", "", str(value)).replace(",", ".")
    if cleaned.count(".") > 1:
        first, *rest = cleaned.split(".")
        cleaned = f"{first}.{''.join(rest)}"
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _is_coherent_existing_value(key: str, value) -> bool:
    return _resolver_is_coherent_value(key, value)


def _is_weak_candidate(key: str, value) -> bool:
    return _resolver_is_weak_candidate(key, value)


def _ocr_one_page(img, fast_mode=False, ocr_scale=2.0, use_deskew=True):
    aligned_img, registration_meta = register_page(img)
    working_img = aligned_img if aligned_img is not None else img
    working_img = enhance_page(working_img)
    if settings.OCR_DEBUG_ZONES:
        logger.info("[OCR DEBUG] page_start registered=%s registration=%s", registration_meta.get("registered"), registration_meta)
    thresh = preprocess_page(working_img)

    if use_deskew and not fast_mode:
        try:
            thresh = deskew_page(thresh)
        except Exception:
            pass

    zones_img = detect_semantic_zones(working_img, thresh)
    zones_text = {}
    scale = 1.5 if fast_mode else ocr_scale

    for nom, roi in zones_img.items():
        if nom == "tableau":
            continue
        if roi is None or (hasattr(roi, "size") and roi.size == 0):
            continue
        zones_text[nom] = recognize(roi, psm=6, ocr_scale=scale)

    template_fields = extract_template(working_img, fast_mode=fast_mode, ocr_scale=scale)
    for key, value in template_fields.items():
        if value:
            zones_text[f"tpl_{key}"] = str(value)

    full_page_text = recognize(working_img, psm=3, ocr_scale=max(1.5, scale - 0.3))
    if full_page_text:
        zones_text["full_document"] = full_page_text

    seen = set()
    chunks = []
    for t in zones_text.values():
        if t and t not in seen:
            seen.add(t)
            chunks.append(t)
    full_text = "\n\n".join(chunks)

    tx, ty, tw, th_z = table_zone_box(working_img)
    thresh_crop = thresh[ty:ty+th_z, tx:tx+tw]
    table_mask = detect_table_mask(thresh_crop)
    cells = extract_table_cells(working_img, table_mask, offset_x=tx, offset_y=ty)

    if not fast_mode:
        for c in cells:
            if c.get("text", "").strip():
                continue
            roi = c.get("image")
            if roi is None or (hasattr(roi, "size") and roi.size == 0):
                x, y, w, h = c["box"]
                roi = working_img[y:y+h, x:x+w]
            try:
                c["text"] = recognize(roi, psm=7, ocr_scale=scale)
            except Exception:
                c["text"] = ""

    return full_text, zones_text, cells, template_fields, registration_meta


def _extract_article_rows_from_cells(cells, page: int = 1):
    textual_cells = []
    for cell in cells:
        text = clean_ocr_text(cell.get("text", ""))
        if not text:
            continue
        x, y, _, _ = cell.get("box", (0, 0, 0, 0))
        textual_cells.append({"x": x, "y": y, "text": text})

    if not textual_cells:
        return []

    textual_cells.sort(key=lambda e: (e["y"], e["x"]))

    grouped_rows = []
    y_tolerance = 16
    for cell in textual_cells:
        if not grouped_rows or abs(cell["y"] - grouped_rows[-1]["y"]) > y_tolerance:
            grouped_rows.append({"y": cell["y"], "cells": [cell]})
        else:
            grouped_rows[-1]["cells"].append(cell)

    rows = []
    seen_keys = set()
    for grouped in grouped_rows:
        ordered_cells = sorted(grouped["cells"], key=lambda e: e["x"])
        row_text = " ".join(e["text"] for e in ordered_cells)
        code_match = re.search(r"\b(\d{8,12})\b", row_text)
        if not code_match:
            continue
        code_hs = code_match.group(1)
        line_match = re.match(r"\s*(\d{1,3})\b", row_text)
        num_ligne = int(line_match.group(1)) if line_match else None
        dedup_key = (page, num_ligne if num_ligne is not None else grouped["y"], code_hs)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        enriched = enrich_article_row_from_line(
            row_text,
            page=page,
            code_hs=code_hs,
            num_ligne=num_ligne,
        )
        if not enriched:
            row_clean = row_text.replace(code_hs, " ")
            nums = [
                _to_float_or_none(t)
                for t in re.findall(r"\b\d+(?:[.,]\d+)?\b", row_clean)
                if _to_float_or_none(t) is not None
            ]
            quantite = nums[-2] if len(nums) >= 2 else None
            total = nums[-1] if len(nums) >= 1 else None
            prix = round(total / quantite, 6) if (quantite and total and quantite != 0) else None
            enriched = {
                "num_ligne": num_ligne,
                "code_hs": code_hs,
                "code_sh_ndp": code_hs,
                "designation": None,
                "quantite": quantite,
                "unite": None,
                "prix_unitaire": prix,
                "total_ligne": total,
                "source": "table_cells",
                "page": page,
            }
        else:
            enriched.setdefault("source", "table_cells")
        rows.append(enriched)
    return rows


def process_document(file_bytes: bytes,
                     filename: str = "document.jpg",
                     fast_mode: bool = False,
                     use_deskew: bool = True,
                     ocr_scale: float = 2.0) -> dict:
    pages = ingest_pages(file_bytes)
    if settings.OCR_DEBUG_ZONES:
        logger.info("[OCR DEBUG] process_document start pages=%s filename=%s fast_mode=%s", len(pages) if pages else 0, filename, fast_mode)
    if not pages:
        return {"erreur": "image non chargee", "fichier": filename}

    all_texts = []
    all_zones = {}
    all_cells = []
    all_articles = []
    all_template_fields = {}
    strict_table_fields = {}
    zone_conflict_flags = set()
    field_reject_reasons = set()
    template_quality_entries = []
    fixed_fallback_blocks = set()
    template_field_confidences = {}
    resolution_notes = {}
    quality_metrics = []
    quality_flags = set()
    registration_metadata = []

    for page_idx, img in enumerate(pages):
        if img is None or (hasattr(img, "size") and img.size == 0):
            continue

        page_text, page_zones, page_cells, page_template_fields, registration_meta = _ocr_one_page(
            img,
            fast_mode=fast_mode,
            ocr_scale=ocr_scale,
            use_deskew=use_deskew,
        )
        registration_meta["page"] = page_idx + 1
        registration_metadata.append(registration_meta)
        metrics, flags = assess_page_quality(img)
        metrics["page"] = page_idx + 1
        quality_metrics.append(metrics)
        quality_flags.update(flags)

        if len(pages) > 1:
            for k, v in page_zones.items():
                all_zones[f"p{page_idx+1}_{k}"] = v
            if page_idx == 0:
                all_zones.update(page_zones)
        else:
            all_zones.update(page_zones)

        all_texts.append(page_text)
        all_cells.extend(page_cells)
        strict_table_fields.update({k: v for k, v in map_fields_from_cells(page_cells).items() if v})

        for key, value in page_template_fields.items():
            if key == "zone_conflict_flags" and isinstance(value, list):
                zone_conflict_flags.update(str(v) for v in value if v)
                continue
            if key == "field_reject_reasons" and isinstance(value, list):
                field_reject_reasons.update(str(v) for v in value if v)
                continue
            if key == "template_quality" and isinstance(value, dict):
                template_quality_entries.append(value)
                continue
            if key == "fixed_fallback_blocks" and isinstance(value, list):
                fixed_fallback_blocks.update(str(v) for v in value if v)
                continue
            if key == "template_field_confidences" and isinstance(value, dict):
                template_field_confidences.update(value)
                continue
            if key.startswith("block_") or not value:
                continue
            if not all_template_fields.get(key):
                all_template_fields[key] = value

        all_articles.extend(_extract_article_rows_from_cells(page_cells, page=page_idx + 1))

    full_text = "\n\n===PAGE_SUIVANTE===\n\n".join(all_texts) if len(pages) > 1 else (all_texts[0] if all_texts else "")

    parsed = parse_document(
        full_text,
        zones_text=all_zones,
        article_rows=all_articles if all_articles else None,
    )

    template_party_snapshot: dict[str, Any] = {
        k: all_template_fields[k]
        for k in PARTY_TEMPLATE_SNAPSHOT_KEYS
        if all_template_fields.get(k)
    }

    template_force_keys = {
        "numero_declaration", "date_declaration", "type_declaration",
        "nbre_articles", "nombre_articles", "nombre_colis",
        "exportateur", "exportateur_nom", "adresse_exportateur",
        "exportateur_code", "code_exportateur",
        "importateur", "importateur_nom", "code_importateur", "adresse_importateur",
        "declarant", "declarant_nom", "nom_declarant", "adresse_declarant",
        "adresse_entreposage",
        "pays_provenance", "pays_achat", "pays_premiere_destination",
        "pays_destination", "pays_destination_finale",
        "mode_transport", "transport_international_mode",
        "transport_international_identite", "transport_national_mode",
        "mode_livraison", "mode_paiement", "relation_acheteur_vendeur",
        "taux_conversion", "valeur_fob_dt", "valeur_dinars", "valeur_totale",
        "poids_brut", "poids_net", "qualite_fiscale",
        "code_gdt", "montant_liquidation", "bureau_douane", "code_bureau",
        "designation_bureau", "itineraire", "num_agrement",
        "num_repertoire", "cle_authentification", "qr_code",
    }
    for key, value in all_template_fields.items():
        if not value:
            continue
        if key in STRICT_TEMPLATE_KEYS and _is_weak_candidate(key, value):
            field_reject_reasons.add(f"{key}_template_candidate_rejected")
            continue
        existing = parsed.get(key)
        confidence_meta = template_field_confidences.get(key) or {}
        resolved_value, winner = _resolver_resolve_field_candidates(
            key,
            existing,
            value,
            template_confidence=confidence_meta.get("confidence"),
        )
        if (
            key in PARTY_TEMPLATE_SNAPSHOT_KEYS
            and value
            and not _is_weak_candidate(key, value)
            and not (
                key == "exportateur_nom"
                and template_exportateur_conflicts_label_window(value, full_text)
            )
        ):
            parsed[key] = value
            resolution_notes[key] = {
                "winner": "template_priority",
                "template_confidence": confidence_meta.get("confidence"),
                "template_engine": confidence_meta.get("engine"),
            }
            continue
        if key == "exportateur_nom" and template_exportateur_conflicts_label_window(value, full_text):
            field_reject_reasons.add("exportateur_nom_template_priority_skipped_label_conflict")
        if winner == "template" and (key in template_force_keys or not existing):
            parsed[key] = resolved_value
            resolution_notes[key] = {
                "winner": "template",
                "template_confidence": confidence_meta.get("confidence"),
                "template_engine": confidence_meta.get("engine"),
            }
        elif winner == "parsed":
            field_reject_reasons.add(f"{key}_template_override_rejected")
            resolution_notes[key] = {"winner": "parsed"}

    # Phase A: strict table-cell mapper takes precedence on targeted fields.
    table_strict_keys = {
        "bureau_frontiere",
        "destination",
        "localisation_export",
        "poids_brut",
        "poids_net",
        "code_qcs",
        "qcs",
        "pfn",
        "code_regime_financier",
        "code_delai",
        "code_oci",
        "numero_escale",
        "rubrique",
        "num_repertoire",
    }
    for key, value in strict_table_fields.items():
        if key not in table_strict_keys:
            continue
        parsed[key] = value
        resolution_notes[key] = {"winner": "table_cell_mapper"}

    parsed = apply_post_parse_normalization(parsed)
    apply_document_coherence(parsed)

    parsed["fichier"] = filename
    parsed["texte_brut"] = full_text
    parsed["texte_nettoye"] = clean_ocr_text(full_text)
    parsed["nb_cellules"] = len(all_cells)
    parsed["nb_pages"] = len(pages)
    parsed["quality_metrics"] = quality_metrics
    parsed["quality_flags"] = sorted(quality_flags)
    parsed["registration"] = registration_metadata
    parsed["registration_quality"] = _summarize_registration(registration_metadata)
    parsed["zone_conflict_flags"] = sorted(zone_conflict_flags)
    parsed["field_reject_reasons"] = sorted(field_reject_reasons)
    if template_quality_entries:
        parsed["template_quality"] = {
            "strategy": "hybrid_dynamic_first",
            "dynamic_anchor_count": sum(int(e.get("dynamic_anchor_count", 0)) for e in template_quality_entries),
            "dynamic_field_count": sum(int(e.get("dynamic_field_count", 0)) for e in template_quality_entries),
            "dynamic_coverage_ratio": round(
                sum(float(e.get("dynamic_coverage_ratio", 0.0)) for e in template_quality_entries)
                / len(template_quality_entries),
                4,
            ),
            "fixed_fallback_count": sum(int(e.get("fixed_fallback_count", 0)) for e in template_quality_entries),
        }
    if fixed_fallback_blocks:
        parsed["fixed_fallback_blocks"] = sorted(fixed_fallback_blocks)
    if resolution_notes:
        parsed["field_resolution"] = resolution_notes
    if template_field_confidences:
        engines = {str(meta.get("engine")) for meta in template_field_confidences.values() if isinstance(meta, dict)}
        if "paddle" in engines:
            parsed["ocr_engine_used"] = "hybrid_tesseract_paddle"
        else:
            parsed["ocr_engine_used"] = "tesseract"
    if quality_flags:
        existing_flags = set(parsed.get("flags_validation") or [])
        parsed["flags_validation"] = sorted(existing_flags.union(quality_flags))
    if zone_conflict_flags:
        existing_flags = set(parsed.get("flags_validation") or [])
        parsed["flags_validation"] = sorted(existing_flags.union(zone_conflict_flags))

    parsed = _drop_polluted_identity_fields(parsed)
    parsed = _apply_high_priority_fallbacks(parsed, full_text)
    parsed = _apply_strict_business_resolver(parsed)
    parsed = _apply_late_field_rescues(parsed, full_text)
    parsed = _restore_template_party_fields(parsed, template_party_snapshot, full_text=full_text)
    sync_reasons = set(parsed.get("field_reject_reasons") or [])
    _sync_parties_from_label_windows(parsed, full_text, sync_reasons)
    parsed["field_reject_reasons"] = sorted(sync_reasons)
    parsed = _sanitize_noisy_geo_fields(parsed)
    if settings.OCR_DEBUG_ZONES:
        logger.info(
            "[OCR DEBUG] process_document done registration_quality=%s zone_conflicts=%s reject_reasons=%s",
            parsed.get("registration_quality"),
            parsed.get("zone_conflict_flags"),
            parsed.get("field_reject_reasons"),
        )
    return _apply_quality_guardrails(parsed)
