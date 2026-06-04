"""Parsing stage wrapper."""

from app.services.parser_service import parse_document_text


def parse_document(full_text, *, zones_text=None, article_rows=None):
    return parse_document_text(full_text, zones_text=zones_text, article_rows=article_rows)
