"""Contrôle qualité document à l'upload (partie 1 — résolution, flou, contraste)."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.services.quality.image_quality import assess_image_quality
from app.services.vision.preprocessing import load_image


def _estimate_dpi(width_px: int, height_px: int) -> float:
    """Estime le DPI en supposant une page A4 (210×297 mm)."""
    dpi_w = width_px / 8.27
    dpi_h = height_px / 11.69
    return round(min(dpi_w, dpi_h), 1)


def assess_upload_document(file_bytes: bytes, content_type: str | None = None) -> dict[str, Any]:
    """
    Évalue le fichier avant OCR.
    Retourne métriques, avertissements et éventuel blocage (si OCR_QUALITY_BLOCK_ON_FAIL).
    """
    warnings: list[str] = []
    errors: list[str] = []
    metrics: dict[str, Any] = {"content_type": content_type or ""}

    if not file_bytes:
        return {
            "ok": False,
            "warnings": warnings,
            "errors": ["fichier_vide"],
            "metrics": metrics,
            "block": True,
        }

    metrics["file_size_bytes"] = len(file_bytes)

    pages = load_image(file_bytes)
    if not pages:
        errors.append("image_non_chargee")
        return {
            "ok": False,
            "warnings": warnings,
            "errors": errors,
            "metrics": metrics,
            "block": bool(settings.OCR_QUALITY_BLOCK_ON_FAIL),
        }

    img = pages[0]
    h, w = img.shape[:2]
    metrics["width_px"] = w
    metrics["height_px"] = h
    metrics["page_count"] = len(pages)
    metrics["estimated_dpi"] = _estimate_dpi(w, h)

    if w < settings.OCR_MIN_PAGE_WIDTH:
        warnings.append("resolution_width_low")
    if h < settings.OCR_MIN_PAGE_HEIGHT:
        warnings.append("resolution_height_low")
    if metrics["estimated_dpi"] < settings.OCR_MIN_ESTIMATED_DPI:
        warnings.append("estimated_dpi_low")

    page_metrics, flags = assess_image_quality(img)
    metrics.update(page_metrics)
    metrics["quality_flags"] = flags

    if page_metrics.get("blur_score", 0) < settings.OCR_MIN_BLUR_SCORE:
        warnings.append("image_blurry")
    for flag in flags:
        if flag not in warnings:
            warnings.append(flag)

    # JPEG très compressé (heuristique sur taille / pixels)
    if content_type in ("image/jpeg", "image/jpg") and len(file_bytes) < (w * h) // 12:
        warnings.append("jpeg_heavily_compressed")

    strict = settings.OCR_QUALITY_STRICT
    block_on_fail = settings.OCR_QUALITY_BLOCK_ON_FAIL
    critical = {"image_non_chargee", "fichier_vide"}
    if strict:
        critical |= {
            "resolution_width_low",
            "resolution_height_low",
            "estimated_dpi_low",
            "image_blurry",
        }

    for code in warnings:
        if code in critical:
            errors.append(code)

    block = block_on_fail and bool(errors)
    ok = not errors

    return {
        "ok": ok,
        "warnings": warnings,
        "errors": errors,
        "metrics": metrics,
        "block": block,
        "recommendations": _recommendations(warnings),
    }


def _recommendations(warnings: list[str]) -> list[str]:
    tips: list[str] = []
    mapping = {
        "resolution_width_low": "Utilisez un scan au moins 1400 px de large (idéal 300 DPI sur A4).",
        "resolution_height_low": "Augmentez la hauteur du scan (page entière visible).",
        "estimated_dpi_low": "Numérisez en 300 DPI ou exportez le PDF en haute résolution.",
        "image_blurry": "Rescannez avec mise au point nette ou trépied.",
        "low_contrast": "Augmentez le contraste ou désactivez le mode économie d'encre.",
        "underexposed": "Scan plus clair ou correction de luminosité.",
        "overexposed": "Réduisez la luminosité du scan.",
        "jpeg_heavily_compressed": "Préférez PNG, TIFF ou PDF pour limiter les artefacts.",
    }
    for w in warnings:
        if w in mapping:
            tips.append(mapping[w])
    return tips
