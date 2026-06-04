"""Exporter, importateur, déclarant — extraction générique neutre (sans marques imposées)."""

from __future__ import annotations

from .generic_party_extraction import apply_generic_parties_to_data


def extract_parties_fields(data, source):
    reasons: set[str] = set()
    apply_generic_parties_to_data(data, source, reasons=reasons)
