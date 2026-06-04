"""Template extraction stage."""

from app.services.template_extractor import extract_template_fields


def extract_template(img, *, fast_mode=False, ocr_scale=2.0):
    return extract_template_fields(img, fast_mode=fast_mode, ocr_scale=ocr_scale)
