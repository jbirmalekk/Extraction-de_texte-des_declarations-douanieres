"""Currency, PTFD, conversion, FOB totals."""

from __future__ import annotations

import re

from .customs_helpers import (
    _clean_amount,
    _float_amount,
    _set_amount_field,
    _set_field,
)


def extract_financial_fields(data, source):
    money_match = re.search(r"\b(USD|EUR|GBP|TND|CHF|JPY|CAD)\s+(\d{3,12}[,.]\d{3})\b", source, re.IGNORECASE)
    if money_match:
        _set_field(data, "devise", money_match.group(1).upper(), force=True)
        _set_amount_field(data, "montant_ptfn", money_match.group(2), force=True)

    conversion_match = re.search(
        r"(?:conversion|facturation|EXPORT)[\s\S]{0,220}?(\d{1,2}[,.]\d{6,8})\s+(\d{4,12}\s*[,.]\s*\d{3})",
        source,
        re.IGNORECASE,
    )
    if conversion_match:
        _set_amount_field(data, "taux_conversion", conversion_match.group(1), force=True)
        total_amount = _clean_amount(conversion_match.group(2))
        _set_amount_field(data, "valeur_fob_dt", total_amount, force=True)
        _set_amount_field(data, "valeur_dinars", total_amount, force=True)
        _set_amount_field(data, "valeur_totale", total_amount, force=True)
    else:
        amount = _float_amount(data.get("montant_ptfn"))
        rate = _float_amount(data.get("taux_conversion"))
        if amount is not None and rate is not None:
            computed_value = amount * rate
            computed = f"{computed_value:.3f}"
            current = _float_amount(data.get("valeur_fob_dt"))
            if current is None or current < computed_value * 0.8:
                _set_amount_field(data, "valeur_fob_dt", computed, force=True)
                _set_amount_field(data, "valeur_dinars", computed, force=True)
                _set_amount_field(data, "valeur_totale", computed, force=True)
