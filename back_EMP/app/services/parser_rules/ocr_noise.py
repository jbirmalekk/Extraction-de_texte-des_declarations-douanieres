"""OCR noise normalization for customs text."""

from __future__ import annotations

import re

OCR_NOISE_RULES = [
    (r"\bCUSTPMS\b", "CUSTOMS"),
    (r"\bCUSTPMS\b", "CUSTOMS"),
    (r"\bDECTARATION\b", "DECLARATION"),
    (r"\bDECLARATON\b", "DECLARATION"),
    (r"\bIMPORTATEAR\b", "IMPORTATEUR"),
    (r"\bIMPRIM[ÉE]\b", "IMPRIME"),
    (r"\bMAYEN\b", "MOYEN"),
    (r"\bPATER\b", "PAYS"),
    (r"\bPAYS\s+DE\s+PREMIGRE\b", "PAYS DE PREMIERE"),
    (r"\bU5D\b", "USD"),
    (r"\bUSO\b", "USD"),
    (r"\bUSP\b", "USD"),
    (r"\bPTEN\b", "PTFN"),
    (r"\bOCB\b", "QCS"),
    (r"\bACS\b", "QCS"),
    (r"\bPOIDA\b", "POIDS"),
    (r"\bPAIDA\b", "POIDS"),
    (r"\bDOUANE\s+COEF\.?\s+D['’]AJUSTE\w*\b", "DOUANE COEF. D'AJUSTEMENT"),
    (r"\bSAT\b", "USA"),
    (r"\bU5A\b", "USA"),
]


def normalize_ocr_noise(text: str) -> str:
    if not text:
        return ""

    normalized = str(text)
    normalized = normalized.replace("’", "'").replace("`", "'")

    for pattern, replacement in OCR_NOISE_RULES:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

    normalized = re.sub(r"[ \t]{2,}", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()
