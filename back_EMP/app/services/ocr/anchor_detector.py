"""Dynamic anchor detection over customs forms."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

import cv2

from app.services import ocr_engine as _ocr_engine


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
    "exportateur": ("EXPORTATEUR", "EXPORTATEU", "EXPORT"),
    "importateur": ("IMPORTATEUR", "IMPORTAT", "LMPORTATEUR"),
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


def detect_anchors(img) -> dict[str, dict]:
    if img is None or (hasattr(img, "size") and img.size == 0):
        return {}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    proc = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
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

        for name, patterns in ANCHOR_PATTERNS.items():
            score = max(_best_anchor_score(token, patterns), _best_anchor_score(combined, patterns))
            if score >= 0.74:
                weighted_conf = round((conf / 100.0) * 0.6 + score * 0.4, 4)
                if name in anchors and anchors[name]["score"] >= weighted_conf:
                    continue
                anchors[name] = {
                    "x": int(data["left"][i]),
                    "y": int(data["top"][i]),
                    "w": int(data["width"][i]),
                    "h": int(data["height"][i]),
                    "token": token,
                    "conf": conf,
                    "score": weighted_conf,
                }
    return anchors
