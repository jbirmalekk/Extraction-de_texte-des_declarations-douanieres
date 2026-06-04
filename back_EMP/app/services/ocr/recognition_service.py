"""OCR recognition stage (Architecture B: gating + business validation + composite score)."""

from __future__ import annotations

import re
from typing import Any

from app.config import settings
from app.services.field_extractors import (
    business_validates_ocr,
    composite_ocr_score,
    get_field_ocr_profile,
)
from app.services.ocr_engine import ocr_zone_img, clean_text
from .common_normalizer import normalize_ocr_text

try:
    from paddleocr import PaddleOCR  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    PaddleOCR = None
try:
    from paddleocr import PPStructure  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    PPStructure = None

_PADDLE_BY_LANG: dict[str, Any] = {}
_PPSTRUCTURE_INSTANCE = None


def _infer_profile(field_name: str | None, psm: int) -> str:
    name = str(field_name or "").lower()
    if any(k in name for k in ("code", "numero", "num_", "repertoire", "colis", "gdt", "qcs", "delai", "regime")):
        return "numeric"
    if psm in {7, 8}:
        return "short_text"
    if name.startswith("block_"):
        return "block"
    return "general"


def _get_paddle(lang: str | None = None) -> Any:
    global _PADDLE_BY_LANG
    lang_key = (lang or settings.OCR_PADDLE_LANG or "en").strip().lower()
    if lang_key in _PADDLE_BY_LANG:
        return _PADDLE_BY_LANG[lang_key]
    if PaddleOCR is None:
        return None
    try:
        _PADDLE_BY_LANG[lang_key] = PaddleOCR(use_angle_cls=True, lang=lang_key)
    except Exception:
        return None
    return _PADDLE_BY_LANG[lang_key]


def _get_ppstructure() -> Any:
    global _PPSTRUCTURE_INSTANCE
    if _PPSTRUCTURE_INSTANCE is not None:
        return _PPSTRUCTURE_INSTANCE
    if PPStructure is None:
        return None
    _PPSTRUCTURE_INSTANCE = PPStructure()
    return _PPSTRUCTURE_INSTANCE


def _paddle_recognize(roi, *, lang: str | None = None) -> tuple[str, float]:
    engine = _get_paddle(lang)
    if engine is None or roi is None:
        return "", 0.0
    try:
        output = engine.ocr(roi, cls=True)
        if not output:
            return "", 0.0
        parts = []
        confs = []
        for line in output:
            if not line:
                continue
            for _, payload in line:
                if not payload:
                    continue
                txt = str(payload[0] or "").strip()
                if txt:
                    parts.append(txt)
                    try:
                        confs.append(float(payload[1]))
                    except Exception:
                        pass
        if not parts:
            return "", 0.0
        avg = sum(confs) / len(confs) if confs else 0.0
        return " ".join(parts).strip(), round(avg, 4)
    except Exception:
        return "", 0.0


def _ppstructure_recognize(roi) -> tuple[str, float]:
    if not settings.OCR_ENABLE_PPSTRUCTURE:
        return "", 0.0
    engine = _get_ppstructure()
    if engine is None or roi is None:
        return "", 0.0
    try:
        output = engine(roi)
        texts = []
        confs = []
        for block in output or []:
            for line in block.get("res", []) or []:
                txt = str(line.get("text") or "").strip()
                if txt:
                    texts.append(txt)
                    try:
                        confs.append(float(line.get("confidence", 0.0)))
                    except Exception:
                        pass
        if not texts:
            return "", 0.0
        avg = sum(confs) / len(confs) if confs else 0.0
        return " ".join(texts).strip(), round(avg, 4)
    except Exception:
        return "", 0.0


def _run_tesseract(roi, *, psm: int, ocr_scale: float, lang: str, profile: str) -> tuple[str, float, dict[str, Any]]:
    return ocr_zone_img(
        roi,
        psm=psm,
        ocr_scale=ocr_scale,
        lang=lang,
        profile=profile,
        return_confidence=True,
    )


def _dedupe_engine_order(primary: str, fallbacks: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for e in (primary,) + fallbacks:
        el = str(e).lower().strip()
        if el not in {"tesseract", "paddle", "ppstructure"}:
            continue
        if el in seen:
            continue
        seen.add(el)
        out.append(el)
    return out


def recognize_detailed(
    roi,
    *,
    psm=6,
    ocr_scale=2.0,
    lang="fra+eng",
    field_name: str | None = None,
    critical: bool = False,
    allow_fallback: bool = True,
):
    """
    Architecture B — ordre des moteurs piloté par le profil champ ; exécution séquentielle avec early-exit.
    Un moteur secondaire n'est invoqué que si le précédent est invalide métier, vide, ou (si critical) sous le seuil.
    """
    cfg = get_field_ocr_profile(field_name, psm)
    psm_eff = int(cfg.get("psm") or psm)
    profile_cfg = cfg.get("profile")
    profile_for_tesseract = profile_cfg or _infer_profile(field_name, psm_eff)
    profile_for_norm = profile_cfg or _infer_profile(field_name, psm_eff)
    val_kind = cfg.get("validation_kind")
    primary = str(cfg.get("primary") or "paddle").lower().strip()
    fallbacks = tuple(str(x).lower() for x in (cfg.get("fallbacks") or ()))

    if primary == "ppstructure" and not settings.OCR_ENABLE_PPSTRUCTURE:
        primary = "paddle"
        fallbacks = tuple(_dedupe_engine_order("paddle", fallbacks + ("tesseract",)))

    engine_order = _dedupe_engine_order(primary, fallbacks)
    if not allow_fallback:
        engine_order = engine_order[:1]

    threshold = float(settings.OCR_CONFIDENCE_THRESHOLD)
    relax_non_critical = 0.35

    best_cand: dict[str, Any] | None = None
    best_score = -1.0
    engines_tried: list[str] = []

    scale = max(ocr_scale, 2.0)

    for eng in engine_order:
        if eng == "ppstructure" and not settings.OCR_ENABLE_PPSTRUCTURE:
            continue
        if eng == "paddle" and _get_paddle() is None:
            continue
        if eng == "ppstructure" and _get_ppstructure() is None:
            continue

        t_meta: dict[str, Any] = {}
        if eng == "tesseract":
            t_text, t_conf, t_meta = _run_tesseract(
                roi,
                psm=psm_eff,
                ocr_scale=scale,
                lang=lang,
                profile=profile_for_tesseract,
            )
            raw_text, conf = t_text, float(t_conf)
        elif eng == "paddle":
            raw_text, conf = _paddle_recognize(roi)
            t_meta = {"engine": "paddle", "paddle_lang": settings.OCR_PADDLE_LANG}
        else:
            raw_text, conf = _ppstructure_recognize(roi)
            t_meta = {"engine": "ppstructure"}

        engines_tried.append(eng)
        normalized = normalize_ocr_text(raw_text or "", field_name=field_name, profile=profile_for_norm)
        biz_ok = business_validates_ocr(val_kind, field_name or "", normalized)

        if eng == "paddle" and not biz_ok:
            fb_lang = (getattr(settings, "OCR_PADDLE_LANG_FALLBACK", "") or "").strip().lower()
            prim = (settings.OCR_PADDLE_LANG or "en").strip().lower()
            fid = (field_name or "").strip().lower()
            if (
                fb_lang
                and fb_lang != prim
                and fid
                in {
                    "exportateur_nom",
                    "exportateur_area",
                    "importateur_nom",
                    "code_importateur",
                    "adresse_exportateur",
                    "adresse_importateur",
                    "declarant_nom",
                }
                and _get_paddle(fb_lang) is not None
            ):
                raw_alt, conf_alt = _paddle_recognize(roi, lang=fb_lang)
                n_alt = normalize_ocr_text(raw_alt or "", field_name=field_name, profile=profile_for_norm)
                b_alt = business_validates_ocr(val_kind, field_name or "", n_alt)
                alpha_cur = len(re.sub(r"[^A-Za-z]", "", normalized))
                alpha_alt = len(re.sub(r"[^A-Za-z]", "", n_alt))
                if b_alt or (alpha_alt >= alpha_cur + 3 and float(conf_alt) >= float(conf) * 0.85):
                    raw_text, conf = raw_alt, float(conf_alt)
                    normalized = n_alt
                    biz_ok = b_alt
                    t_meta = {**t_meta, "paddle_lang": fb_lang, "paddle_lang_fallback": True}
                    engines_tried.append(f"paddle:{fb_lang}")

        comp = composite_ocr_score(confidence=conf, business_valid=biz_ok)

        cand = {
            "text": normalized,
            "confidence": float(conf),
            "engine": eng,
            "profile": profile_for_norm,
            "meta": {**t_meta, "engines_tried": list(engines_tried), "business_valid": biz_ok, "composite_score": comp},
            "fallback_used": eng != engine_order[0],
        }

        if comp > best_score or best_cand is None:
            best_score = comp
            best_cand = cand

        if biz_ok and normalized and conf >= threshold:
            best_cand = cand
            break
        if biz_ok and normalized and not critical and conf >= relax_non_critical:
            best_cand = cand
            break

    if best_cand is None:
        t_text, t_conf, t_meta = _run_tesseract(
            roi,
            psm=psm_eff,
            ocr_scale=scale,
            lang=lang,
            profile=profile_for_tesseract,
        )
        normalized = normalize_ocr_text(t_text or "", field_name=field_name, profile=profile_for_norm)
        best_cand = {
            "text": normalized,
            "confidence": float(t_conf),
            "engine": "tesseract",
            "profile": profile_for_norm,
            "meta": {**t_meta, "engines_tried": ["tesseract"], "business_valid": False, "composite_score": 0.0},
            "fallback_used": False,
        }

    # Legacy-style confidence fallback: si critical + toujours faible confiance, tenter l'autre moteur principal du couple paddle/tesseract
    if allow_fallback and critical and best_cand["confidence"] < threshold:
        other = "paddle" if best_cand["engine"] == "tesseract" else "tesseract"
        if other not in engines_tried and other in {"paddle", "tesseract"}:
            if other == "paddle" and _get_paddle() is not None:
                p_text, p_conf = _paddle_recognize(roi)
                pn = normalize_ocr_text(p_text or "", field_name=field_name, profile=profile_for_norm)
                pb = business_validates_ocr(val_kind, field_name or "", pn)
                if p_conf > best_cand["confidence"] or (pb and not business_validates_ocr(val_kind, field_name or "", best_cand["text"])):
                    best_cand.update(
                        {
                            "text": pn,
                            "confidence": float(p_conf),
                            "engine": "paddle",
                            "fallback_used": True,
                            "meta": {
                                **best_cand.get("meta", {}),
                                "engines_tried": engines_tried + ["paddle"],
                                "business_valid": pb,
                                "composite_score": composite_ocr_score(confidence=p_conf, business_valid=pb),
                            },
                        }
                    )
            elif other == "tesseract":
                t_text, t_conf, t_meta = _run_tesseract(
                    roi,
                    psm=psm_eff,
                    ocr_scale=scale,
                    lang=lang,
                    profile=profile_for_tesseract,
                )
                tn = normalize_ocr_text(t_text or "", field_name=field_name, profile=profile_for_norm)
                tb = business_validates_ocr(val_kind, field_name or "", tn)
                if t_conf > best_cand["confidence"] or (tb and not business_validates_ocr(val_kind, field_name or "", best_cand["text"])):
                    best_cand.update(
                        {
                            "text": tn,
                            "confidence": float(t_conf),
                            "engine": "tesseract",
                            "fallback_used": True,
                            "meta": {
                                **t_meta,
                                "engines_tried": engines_tried + ["tesseract"],
                                "business_valid": tb,
                                "composite_score": composite_ocr_score(confidence=t_conf, business_valid=tb),
                            },
                        }
                    )

    return best_cand


def recognize(roi, *, psm=6, ocr_scale=2.0, lang="fra+eng"):
    details = recognize_detailed(roi, psm=psm, ocr_scale=ocr_scale, lang=lang, field_name=None, critical=False)
    return details["text"]


def clean_ocr_text(text):
    return clean_text(text)
