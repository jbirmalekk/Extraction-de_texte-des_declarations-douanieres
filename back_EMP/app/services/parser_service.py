"""Parser service facade to stabilize parser usage across the pipeline."""

from __future__ import annotations

from .parser_v2 import parse_fields
from .semantic_parser import apply_semantic_normalization
from .field_extractors import build_field_confidences


def parse_document_text(text: str, zones_text=None, article_rows=None) -> dict:
    """
    Single stable entrypoint for OCR parsing.
    `parse_fields` already applies validation/scoring internally.
    """
    parsed = parse_fields(text, zones_text=zones_text, article_rows=article_rows)
    parsed = apply_semantic_normalization(parsed)
    parsed["field_confidences"] = build_field_confidences(parsed)
    return parsed
