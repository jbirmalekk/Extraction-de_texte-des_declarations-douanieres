"""OCR layout stage: semantic zones/table layout helpers."""

from app.services.vision.zones import (
    detect_zones_semantiques,
    get_zone_box,
    detect_table,
    extract_cells,
)


def detect_semantic_zones(img, thresh):
    return detect_zones_semantiques(img, thresh)


def table_zone_box(img):
    return get_zone_box(img, "tableau")


def detect_table_mask(thresh_crop):
    return detect_table(thresh_crop)


def extract_table_cells(img, table_mask, *, offset_x=0, offset_y=0):
    return extract_cells(img, table_mask, offset_x=offset_x, offset_y=offset_y)
