"""Dynamic anchor detection over customs forms."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

import cv2

from app.services.vision import ocr_engine as _ocr_engine


def _normalize_token(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper().strip()
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def _fuzzy_match(token: str, pattern: str) -> float:
    return SequenceMatcher(None, token, pattern).ratio()


def _best_anchor_score(token: str, patterns: tuple[str, ...]) -> float:
    exact = 1.0 if any(pattern in token for pattern in patterns) else 0.0
    fuzzy = max((_fuzzy_match(token, p) for p in patterns), default=0.0)
    return max(exact, fuzzy)


ANCHOR_PATTERNS = {
    # "XPORTAT" / "MPORTAT" discriminent E(x)portateur vs I(m)portateur (1 lettre d'écart sinon).
    "exportateur": ("EXPORTATEUR", "XPORTAT", "EXPORTATEU"),
    "importateur": ("IMPORTATEUR", "MPORTAT", "LMPORTATEUR"),
    "declarant": ("DECLARANT", "DECLAR", "DCLARANT"),
    "colis": ("COLIS", "NBRECOLIS", "NOMBRECOLIS"),
    "provenance": ("PROVENANCE",),
    "achat": ("ACHAT",),
    # Avoid bare "PREMIERE" / "DESTINATION" — they match unrelated labels and shift country ROIs.
    "premiere_destination": ("PREMIEREDESTINATION", "PREMIEREDESTINAT", "1EREDESTINATION"),
    "destination_finale": ("DESTINATIONFINALE", "DESTINATIONDEFINITIVE", "DESTINATIONDEFINIT"),
    "regime_financier": ("REGLEMENTFINANCIER", "CREG", "REGIMEFINANCIER"),
    "delai": ("DELAI", "CDELAI"),
    "transport": ("MOYENDETRANSPORT", "TRANSPORT"),
    "livraison": ("LIVRAISON",),
}


def _preprocess_for_anchors(img):
    """Agrandit + normalise le contraste pour rendre les libellés lisibles.

    Sur scans faibles/surexposés, l'OCR des ancres échoue sans ce prétraitement.
    Retourne (image_traitée, facteur_d_echelle) ; les coordonnées OCR devront
    être divisées par le facteur pour revenir dans l'espace de l'image d'entrée.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    # Vise ~2600px de large pour l'OCR des libellés, avec un minimum d'agrandissement.
    factor = 2600.0 / float(max(1, w))
    factor = max(1.9, min(3.0, factor))
    if abs(factor - 1.0) > 1e-3:
        gray = cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    proc = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return proc, factor


def detect_anchors(img) -> dict[str, dict]:
    if img is None or (hasattr(img, "size") and img.size == 0):
        return {}

    proc, factor = _preprocess_for_anchors(img)
    inv = 1.0 / factor
    data = _ocr_engine.pytesseract.image_to_data(
        proc,
        config="--psm 6 -l fra+eng",
        output_type=_ocr_engine.pytesseract.Output.DICT,
    )

    anchors: dict[str, dict] = {}
    n = len(data.get("text", []))
    min_anchor_conf = 12.0
    for i in range(n):
        raw = (data["text"][i] or "").strip()
        if not raw:
            continue
        conf = float(data["conf"][i]) if str(data["conf"][i]).strip() not in {"", "-1"} else -1.0
        if conf < min_anchor_conf:
            continue
        token = _normalize_token(raw)
        if len(token) < 3:
            continue
        next_token = ""
        if i + 1 < n:
            next_token = _normalize_token(data["text"][i + 1] or "")
        combined = f"{token}{next_token}" if next_token else token

        # Un mot n'est affecté qu'à SA MEILLEURE ancre (évite qu'EXPORTATEUR
        # revendique aussi IMPORTATEUR par similarité).
        best_name = None
        best_score = 0.0
        for name, patterns in ANCHOR_PATTERNS.items():
            score = max(_best_anchor_score(token, patterns), _best_anchor_score(combined, patterns))
            if score > best_score:
                best_score = score
                best_name = name
        if best_name is None or best_score < 0.74:
            continue

        weighted_conf = round((conf / 100.0) * 0.6 + best_score * 0.4, 4)
        if best_name in anchors and anchors[best_name]["score"] >= weighted_conf:
            continue
        # Remise à l'échelle vers l'espace de l'image d'entrée.
        anchors[best_name] = {
            "x": int(round(int(data["left"][i]) * inv)),
            "y": int(round(int(data["top"][i]) * inv)),
            "w": int(round(int(data["width"][i]) * inv)),
            "h": int(round(int(data["height"][i]) * inv)),
            "token": token,
            "conf": conf,
            "score": weighted_conf,
        }
    return anchors
