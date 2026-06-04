"""OCR ingest stage: load input bytes into page images."""

from app.services.preprocessing import load_image


def ingest_pages(file_bytes: bytes):
    return load_image(file_bytes)
