"""OCR service package."""


def process_document(*args, **kwargs):
    # Lazy import avoids circular import between template and orchestrator layers.
    from .orchestrator import process_document as _process_document

    return _process_document(*args, **kwargs)


__all__ = ["process_document"]
