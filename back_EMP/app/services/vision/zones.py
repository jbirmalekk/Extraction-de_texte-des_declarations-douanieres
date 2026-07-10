# Copie exacte de la Cellule 7 du notebook
import cv2
import numpy as np

SEMANTIC_ZONES = {
    "header"        : (0.00, 0.12, 0.00, 1.00),
    "header_right"  : (0.00, 0.12, 0.45, 1.00),
    "exportateur"   : (0.05, 0.18, 0.00, 0.52),
    "importateur"   : (0.14, 0.26, 0.00, 0.60),
    "declarant"     : (0.22, 0.34, 0.00, 0.60),
    "pays"          : (0.22, 0.36, 0.45, 1.00),
    "transport"     : (0.27, 0.44, 0.00, 1.00),   # ← NOUVEAU : toute la section transport
    "conditions"    : (0.27, 0.42, 0.00, 1.00),
    "finances"      : (0.25, 0.42, 0.45, 1.00),
    "fob_zone"      : (0.36, 0.46, 0.00, 1.00),
    "marchandises"  : (0.38, 0.60, 0.00, 1.00),
    "taxes"         : (0.58, 0.76, 0.00, 1.00),
    "liquidation"   : (0.74, 0.90, 0.00, 1.00),
    "final"         : (0.88, 1.00, 0.00, 1.00),
    "tableau"       : (0.38, 0.90, 0.00, 1.00),
}


def _box_from_ratio(img, ratio):
    h, w   = img.shape[:2]
    y1, y2, x1, x2 = ratio
    x1p = max(0, min(w, int(w * x1)))
    x2p = max(0, min(w, int(w * x2)))
    y1p = max(0, min(h, int(h * y1)))
    y2p = max(0, min(h, int(h * y2)))
    if x2p <= x1p: x2p = min(w, x1p + 1)
    if y2p <= y1p: y2p = min(h, y1p + 1)
    return x1p, y1p, x2p - x1p, y2p - y1p


def detect_zones_semantiques(img, thresh=None):
    zones = {}
    for name, ratio in SEMANTIC_ZONES.items():
        x, y, w, h = _box_from_ratio(img, ratio)
        zones[name] = img[y:y+h, x:x+w]
    return zones


def get_zone_box(img, zone_name):
    return _box_from_ratio(img, SEMANTIC_ZONES[zone_name])


def detect_zones(thresh, min_w=80, min_h=20):
    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    zones = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > min_w and h > min_h:
            zones.append((x, y, w, h))
    zones.sort(key=lambda z: z[1])
    return zones


def detect_table(thresh):
    h_k = cv2.getStructuringElement(
        cv2.MORPH_RECT, (max(15, thresh.shape[1] // 20), 1)
    )
    v_k = cv2.getStructuringElement(
        cv2.MORPH_RECT, (1, max(15, thresh.shape[0] // 20))
    )
    return cv2.add(
        cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_k),
        cv2.morphologyEx(thresh, cv2.MORPH_OPEN, v_k)
    )


def extract_cells(img, table_mask, min_w=45, min_h=18,
                  offset_x=0, offset_y=0):
    contours, _ = cv2.findContours(
        table_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    cells = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        abs_x = x + offset_x
        abs_y = y + offset_y
        if w > min_w and h > min_h:
            cells.append({
                "box"  : (abs_x, abs_y, w, h),
                "image": img[abs_y:abs_y+h, abs_x:abs_x+w],
                "text" : ""
            })
    return cells