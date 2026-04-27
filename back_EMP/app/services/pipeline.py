# Copie de la Cellule 14 — process_one adapté backend (sans matplotlib)
import os
import re
import cv2
from .preprocessing import load_image, preprocess, deskew
from .zones import (detect_zones_semantiques, get_zone_box,
                    detect_table, extract_cells)
from .ocr_engine import ocr_zone_img, clean_text
from .parser_v2 import parse_fields


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


def _extract_article_rows_from_cells(cells):
    """Build lightweight article rows from OCR table cells when possible."""
    textual_cells = []
    for cell in cells:
        text = clean_text(cell.get("text", ""))
        if not text:
            continue
        x, y, _, _ = cell.get("box", (0, 0, 0, 0))
        textual_cells.append({"x": x, "y": y, "text": text})

    if not textual_cells:
        return []

    textual_cells.sort(key=lambda entry: (entry["y"], entry["x"]))

    grouped_rows = []
    y_tolerance = 16
    for cell in textual_cells:
        if not grouped_rows or abs(cell["y"] - grouped_rows[-1]["y"]) > y_tolerance:
            grouped_rows.append({"y": cell["y"], "cells": [cell]})
        else:
            grouped_rows[-1]["cells"].append(cell)

    rows = []
    seen_codes = set()

    for grouped in grouped_rows:
        ordered_cells = sorted(grouped["cells"], key=lambda entry: entry["x"])
        row_text = " ".join(entry["text"] for entry in ordered_cells)

        code_match = re.search(r"\b(\d{8,12})\b", row_text)
        if not code_match:
            continue

        code_hs = code_match.group(1)
        if code_hs in seen_codes:
            continue
        seen_codes.add(code_hs)

        line_match = re.match(r"\s*(\d{1,3})\b", row_text)
        num_ligne = int(line_match.group(1)) if line_match else None

        row_without_code = row_text.replace(code_hs, " ")
        numeric_tokens = re.findall(r"\b\d+(?:[.,]\d+)?\b", row_without_code)
        numeric_values = [
            _to_float_or_none(token)
            for token in numeric_tokens
        ]
        numeric_values = [value for value in numeric_values if value is not None]

        quantite = numeric_values[-2] if len(numeric_values) >= 2 else None
        total_ligne = numeric_values[-1] if len(numeric_values) >= 1 else None

        prix_unitaire = None
        if quantite is not None and total_ligne is not None and quantite != 0:
            prix_unitaire = round(total_ligne / quantite, 6)

        rows.append({
            "num_ligne": num_ligne,
            "code_hs": code_hs,
            "designation": None,
            "quantite": quantite,
            "unite": None,
            "prix_unitaire": prix_unitaire,
            "total_ligne": total_ligne,
        })

    return rows


def process_document(file_bytes: bytes,
                     filename: str = "document.jpg",
                     fast_mode: bool = False,
                     use_deskew: bool = True,
                     ocr_scale: float = 1.5) -> dict:
    """
    Pipeline complet OCR — reçoit des bytes (upload FastAPI).
    Retourne un dict JSON avec tous les champs extraits.
    """

    # 1. Chargement depuis bytes
    img = load_image(file_bytes)
    if img is None:
        return {"erreur": "image non chargee", "fichier": filename}

    # 2. Preprocessing
    thresh = preprocess(img)
    if use_deskew:
        thresh = deskew(thresh)

    # 3. OCR zones sémantiques
    zones_img  = detect_zones_semantiques(img, thresh)
    zones_text = {}
    scale      = 1.2 if fast_mode else ocr_scale

    for nom, roi in zones_img.items():
        if nom == "tableau": continue
        if roi is None or roi.size == 0: continue
        zones_text[nom] = ocr_zone_img(roi, psm=6, ocr_scale=scale)

    full_text = "\n\n".join(v for v in zones_text.values() if v)

    # 4. Extraction tableau
    table_box        = get_zone_box(img, "tableau")
    tx, ty, tw, th_z = table_box
    table_mask       = detect_table(thresh[ty:ty+th_z, tx:tx+tw])
    cells            = extract_cells(img, table_mask, offset_x=tx, offset_y=ty)

    # 5. OCR cellules
    if not fast_mode:
        for c in cells:
            if c.get("text","").strip(): continue
            roi = c.get("image")
            if roi is None or (hasattr(roi,"size") and roi.size == 0):
                x, y, w, h = c["box"]
                roi = img[y:y+h, x:x+w]
            try:
                c["text"] = ocr_zone_img(roi, psm=7, ocr_scale=scale)
            except:
                c["text"] = ""

    article_rows = _extract_article_rows_from_cells(cells)

    # 6. Parsing + validation
    parsed = parse_fields(full_text, zones_text=zones_text, article_rows=article_rows)
    parsed["fichier"]        = filename
    parsed["texte_brut"]     = full_text
    parsed["texte_nettoye"]  = clean_text(full_text)
    parsed["nb_cellules"]    = len(cells)

    return parsed