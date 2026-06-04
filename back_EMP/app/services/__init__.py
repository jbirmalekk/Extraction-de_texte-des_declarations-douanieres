"""
Services package.

Imports are resolved lazily so parser-only tools do not load OpenCV/Tesseract.
"""

__all__ = [
    "process_document",
    "load_image",
    "preprocess",
    "deskew",
    "detect_zones",
    "extract_cells",
    "SEMANTIC_ZONES",
    "detect_zones_semantiques",
    "get_zone_box",
    "ocr_zone_img",
    "clean_text",
    "parse_fields",
    "valider_champs",
    "parse_document_text",
    "build_field_confidences",
    "apply_semantic_normalization",
]


def __getattr__(name):
    if name == "process_document":
        from .pipeline import process_document
        return process_document

    if name in {"load_image", "preprocess", "deskew"}:
        from . import preprocessing
        return getattr(preprocessing, name)

    if name in {
        "detect_zones",
        "extract_cells",
        "SEMANTIC_ZONES",
        "detect_zones_semantiques",
        "get_zone_box",
    }:
        from . import zones
        return getattr(zones, name)

    if name in {"ocr_zone_img", "clean_text"}:
        from . import ocr_engine
        return getattr(ocr_engine, name)

    if name in {"parse_fields", "valider_champs"}:
        from . import parser_v2
        return getattr(parser_v2, name)

    if name == "parse_document_text":
        from .parser_service import parse_document_text
        return parse_document_text

    if name == "build_field_confidences":
        from .field_extractors import build_field_confidences
        return build_field_confidences

    if name == "apply_semantic_normalization":
        from .semantic_parser import apply_semantic_normalization
        return apply_semantic_normalization

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
