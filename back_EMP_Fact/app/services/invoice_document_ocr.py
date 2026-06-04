"""
OCR document facture — aligné sur la DUM (Paddle prioritaire, Tesseract secours, prétraitement léger).

Contrairement à l'ancien flux « Tesseract seul », on tente Paddle sur les pages rendues
(PDF scanné / image) avant le repli Tesseract, comme sur back_EMP.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger("app.invoice.ocr")

_PADDLE: Any = None


def _get_paddle():
    global _PADDLE
    if _PADDLE is not None:
        return _PADDLE
    if not settings.OCR_ENABLE_PADDLE:
        return None
    try:
        from paddleocr import PaddleOCR  # type: ignore

        lang = (settings.OCR_PADDLE_LANG or "en").strip().lower()
        _PADDLE = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
    except Exception as exc:
        logger.warning("paddle_init_failed: %s", exc)
        _PADDLE = False
    return _PADDLE if _PADDLE is not False else None


def _configure_tesseract() -> None:
    import pytesseract

    path = (settings.TESSERACT_PATH or "").strip()
    if path:
        pytesseract.pytesseract.tesseract_cmd = path


def _enhance_pil(img):
    """Prétraitement léger (contraste) si OpenCV disponible."""
    if not settings.OCR_PREPROCESS_ENHANCE:
        return img
    try:
        import cv2
        import numpy as np
        from PIL import Image

        gray = np.array(img.convert("L"))
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        return Image.fromarray(enhanced).convert("RGB")
    except Exception:
        return img


def _paddle_text_from_pil(img) -> tuple[str, float]:
    engine = _get_paddle()
    if engine is None:
        return "", 0.0
    try:
        import numpy as np

        arr = np.array(img.convert("RGB"))
        output = engine.ocr(arr, cls=True)
        if not output:
            return "", 0.0
        parts: list[str] = []
        confs: list[float] = []
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
        return "\n".join(parts), avg
    except Exception as exc:
        logger.debug("paddle_page_failed: %s", exc)
        return "", 0.0


def _tesseract_text_from_pil(img) -> str:
    import pytesseract

    _configure_tesseract()
    lang = (settings.OCR_TESSERACT_LANG or "eng").strip()
    return pytesseract.image_to_string(img, lang=lang, config="--oem 3 --psm 6")


def ocr_pil_image(img) -> tuple[str, list[str]]:
    """OCR une image PIL : Tesseract d'abord (facture) ou Paddle selon config."""
    warns: list[str] = []
    img = _enhance_pil(img)

    if settings.OCR_INVOICE_TESSERACT_FIRST:
        try:
            text = _tesseract_text_from_pil(img)
            if text.strip():
                warns.append("engine:tesseract_first")
                return text, warns
            warns.append("tesseract_empty_try_paddle")
        except Exception as exc:
            warns.append(f"tesseract_error:{exc!s}")

    if settings.OCR_ENGINE_PRIMARY.lower() == "paddle" and settings.OCR_ENABLE_PADDLE:
        text, conf = _paddle_text_from_pil(img)
        if text.strip():
            warns.append(f"engine:paddle(conf={conf:.2f})")
            return text, warns
        warns.append("paddle_empty_fallback_tesseract")

    try:
        text = _tesseract_text_from_pil(img)
        if text.strip():
            warns.append("engine:tesseract")
            return text, warns
        warns.append("tesseract_returned_empty")
        return "", warns
    except Exception as exc:
        return "", [f"tesseract_error:{exc!s}"]


def ocr_pdf_rendered(data: bytes, *, max_pages: int | None = None, zoom: float | None = None) -> tuple[str, list[str]]:
    """PDF sans texte embarqué : rendu page(s) + OCR."""
    warns: list[str] = []
    max_pages = max_pages if max_pages is not None else settings.OCR_PDF_MAX_PAGES
    zoom = zoom if zoom is not None else settings.OCR_PDF_ZOOM

    try:
        import fitz
        from PIL import Image
    except ImportError as exc:
        return "", [f"missing_dependency:{exc}"]

    parts: list[str] = []
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        return "", [f"pdf_open:{exc}"]

    try:
        n = min(doc.page_count, max_pages)
        for i in range(n):
            page = doc.load_page(i)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            text, page_warns = ocr_pil_image(img)
            warns.extend(page_warns)
            if text.strip():
                parts.append(text)
    finally:
        doc.close()

    if not parts:
        warns.append("no_text_on_rendered_pdf_pages")
    return "\n\n".join(parts), warns


def ocr_image_bytes(data: bytes) -> tuple[str, list[str]]:
    try:
        from PIL import Image
    except ImportError as exc:
        return "", [f"missing_dependency:{exc}"]
    try:
        img = Image.open(io.BytesIO(data))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        return ocr_pil_image(img)
    except Exception as exc:
        return "", [f"image_ocr:{exc!s}"]
