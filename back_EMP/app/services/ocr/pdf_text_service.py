"""Extraction du texte embarqué des PDF (déclarations douanières digitalisées)."""

from __future__ import annotations

import re
import unicodedata

from app.config import settings


def is_pdf_bytes(data: bytes) -> bool:
    return bool(data) and data[:4] == b"%PDF"


def _meaningful_char_count(text: str) -> int:
    """Compte lettres/chiffres utiles (hors espaces) pour détecter un vrai PDF texte."""
    if not text:
        return 0
    count = 0
    for ch in text:
        if ch.isspace():
            continue
        cat = unicodedata.category(ch)
        if cat[0] in ("L", "N"):
            count += 1
    return count


def read_embedded_pdf_text(data: bytes) -> tuple[str, list[str]]:
    """Lit le texte natif de toutes les pages via PyMuPDF."""
    warnings: list[str] = []
    try:
        import fitz
    except ImportError as exc:
        return "", [f"pymupdf_missing:{exc}"]

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        return "", [f"pdf_open_error:{exc}"]

    parts: list[str] = []
    try:
        for page in doc:
            parts.append(page.get_text("text") or "")
    finally:
        doc.close()

    text = "\n".join(parts)
    if not text.strip():
        warnings.append("pdf_no_embedded_text")
    else:
        warnings.append("pdf_embedded_text_used")
    return text, warnings


def has_sufficient_embedded_text(text: str, *, min_chars: int | None = None) -> bool:
    threshold = min_chars if min_chars is not None else settings.OCR_PDF_TEXT_MIN_CHARS
    return _meaningful_char_count(text) >= max(100, threshold)


def detect_pdf_text_profile(text: str) -> str:
    """Profil léger pour logs / métadonnées."""
    upper = (text or "").upper()
    if "DECLARATION EN DETAIL" in upper or "DÉCLARATION EN DÉTAIL" in upper:
        return "dum_detail"
    if re.search(r"\bSA\s*\d{5,7}\b", upper) or "CERTIFICAT DE DECHARGE" in upper.replace("É", "E"):
        return "sa_text"
    if "DOUANES TUNISIENNES" in upper:
        return "tunisia_customs"
    return "unknown"


def pdf_page_count(data: bytes) -> int:
    try:
        import fitz

        doc = fitz.open(stream=data, filetype="pdf")
        try:
            return int(doc.page_count or 0)
        finally:
            doc.close()
    except Exception:
        return 0
