# Copie de la Cellule 14 — process_one adapté backend (sans matplotlib)
import os
import cv2
from .preprocessing import load_image, preprocess, deskew
from .zones import (detect_zones_semantiques, get_zone_box,
                    detect_table, extract_cells)
from .ocr_engine import ocr_zone_img, clean_text
from .parser import parse_fields


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

    # 6. Parsing + validation
    parsed = parse_fields(full_text, zones_text=zones_text)
    parsed["fichier"]        = filename
    parsed["texte_brut"]     = full_text
    parsed["texte_nettoye"]  = clean_text(full_text)
    parsed["nb_cellules"]    = len(cells)

    return parsed