"""OCR preprocessing stage."""

from app.config import settings
from app.services.vision.preprocessing import preprocess, deskew, enhance_scan


def enhance_page(img):
    if settings.OCR_PREPROCESS_ENHANCE:
        return enhance_scan(img)
    return img


def preprocess_page(img):
    return preprocess(img)


def deskew_page(thresh):
    return deskew(thresh)
