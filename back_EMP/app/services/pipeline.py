"""Compatibility proxy for OCR pipeline entrypoint."""

from app.services.ocr.orchestrator import process_document

__all__ = ["process_document"]
