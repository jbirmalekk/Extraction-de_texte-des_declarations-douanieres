import cv2
import re
import numpy as np
import pytesseract
import os
from typing import Any
from app.config import settings

if settings.TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
elif os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )


def _preprocess_for_ocr(roi, scale):
    """Préprocessing optimisé pour les documents douaniers."""
    # Agrandir
    roi_big = cv2.resize(roi, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_CUBIC)
    # Niveaux de gris
    gray = cv2.cvtColor(roi_big, cv2.COLOR_BGR2GRAY)

    # Débruitage léger
    gray = cv2.GaussianBlur(gray, (1, 1), 0)

    # Binarisation adaptative (meilleure que Otsu pour les documents scannés)
    th_otsu = cv2.threshold(gray, 0, 255,
                            cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    # Sharpen pour améliorer les bords des caractères
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(th_otsu, -1, kernel)

    return sharpened


def _profile_configs(psm: int, lang: str, profile: str | None) -> list[str]:
    profile = (profile or "general").lower()
    if profile in {"numeric", "digits"}:
        return [
            f"--oem 1 --psm {psm} -l {lang} -c tessedit_char_whitelist=0123456789",
            f"--oem 1 --psm 8 -l {lang} -c tessedit_char_whitelist=0123456789",
        ]
    if profile in {"code", "alnum"}:
        return [
            f"--oem 1 --psm {psm} -l {lang} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-./",
            f"--oem 1 --psm 7 -l {lang} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-./",
        ]
    if profile in {"short_text"}:
        return [
            f"--oem 1 --psm {psm} -l {lang}",
            f"--oem 1 --psm 7 -l {lang}",
        ]
    if profile in {"block"}:
        return [
            f"--oem 1 --psm {psm} -l {lang}",
            f"--oem 1 --psm 4 -l {lang}",
            f"--oem 1 --psm 6 -l {lang}",
        ]
    return [
        f"--oem 1 --psm {psm} -l {lang}",
        f"--oem 1 --psm 6 -l {lang}",
        f"--oem 1 --psm 3 -l {lang}",
    ]


def _extract_confidence(img, config: str) -> float:
    try:
        data = pytesseract.image_to_data(img, config=config, output_type=pytesseract.Output.DICT)
        values = []
        for raw in data.get("conf", []):
            try:
                score = float(raw)
            except Exception:
                continue
            if score >= 0:
                values.append(score)
        if not values:
            return 0.0
        return round(sum(values) / (100.0 * len(values)), 4)
    except Exception:
        return 0.0


def ocr_zone_img(
    roi,
    psm=6,
    ocr_scale=2.0,
    lang="fra+eng",
    profile: str | None = None,
    return_confidence: bool = False,
) -> str | tuple[str, float, dict[str, Any]]:
    """OCR robuste — scale 2.0 minimum pour petits caractères."""
    if roi is None or (hasattr(roi, "size") and roi.size == 0):
        if return_confidence:
            return "", 0.0, {"engine": "tesseract", "profile": profile or "general", "attempts": 0}
        return ""
    try:
        processed = _preprocess_for_ocr(roi, max(ocr_scale, 2.0))
        configs = _profile_configs(psm=psm, lang=lang, profile=profile)
        best = ""
        best_conf = 0.0
        best_cfg = ""
        for cfg in configs:
            try:
                t = pytesseract.image_to_string(processed, config=cfg).strip()
                conf = _extract_confidence(processed, cfg) if t else 0.0
                if len(t) > len(best) or (len(t) == len(best) and conf > best_conf):
                    best = t
                    best_conf = conf
                    best_cfg = cfg
            except Exception:
                pass
        if return_confidence:
            return best, best_conf, {
                "engine": "tesseract",
                "profile": profile or "general",
                "attempts": len(configs),
                "config": best_cfg,
            }
        return best
    except Exception as e:
        print(f"ocr_zone_img error: {e}")
        if return_confidence:
            return "", 0.0, {"engine": "tesseract", "profile": profile or "general", "attempts": 0, "error": str(e)}
        return ""


def clean_text(text):
    """
    Nettoyage minimal — garde les caractères utiles.
    Ne PAS utiliser pour le parsing, seulement pour l'affichage.
    """
    if not text:
        return ""
    # Retirer uniquement les caractères vraiment parasites
    # Garder: Latin étendu, chiffres, ponctuation courante
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = re.sub(r'[ \t]{3,}', '  ', text)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text.strip()