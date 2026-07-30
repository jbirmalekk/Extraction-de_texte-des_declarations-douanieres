"""Country / destination fields."""

from __future__ import annotations

import re

from .customs_helpers import (
    _country_label,
    _fold_text,
    _set_field,
)


def extract_country_fields(data, source):
    folded = _fold_text(source)
    country_pattern = (
        r"\b(TN|1N|TM|DE|FR|US|IT|ES|BE|CN|TR|NL|GB)\s+"
        r"(TUNISIE|FRANCE|ALLEMAGNE|U\.?\s*S\.?\s*A\.?|USA|ITALIE|ESPAGNE|"
        r"BELGIQUE|CHINE|TURQUIE|PAYS\s+BAS|ROYAUME\s+UNI)\b"
    )
    country_re = re.compile(country_pattern, re.IGNORECASE)

    def as_pair(match):
        code = match.group(1).upper().replace("1N", "TN").replace("TM", "TN")
        name = re.sub(r"\s+", " ", match.group(2).upper()).replace("U S A", "USA")
        return code, name

    def find_after(label_pattern):
        for label_match in re.finditer(label_pattern, folded, re.IGNORECASE):
            window = folded[label_match.end():label_match.end() + 260]
            match = country_re.search(window)
            if match:
                return as_pair(match)
        return None

    contextual = {
        "pays_provenance": find_after(r"PAYS\s+(?:DE\s+)?PROVENANCE"),
        "pays_achat": find_after(r"PAYS\s+D[' ]?ACHAT"),
        "pays_premiere_destination": find_after(r"(?:PAYS\s+(?:DE\s+)?)?PREMIERE\s+DESTINATION"),
        "pays_destination_finale": find_after(r"(?:PAYS\s+(?:DE\s+)?)?DESTINATION\s+DEFINITIVE"),
    }

    for field, pair in contextual.items():
        if pair:
            _set_field(data, field, _country_label(*pair))

    if contextual["pays_destination_finale"]:
        _set_field(data, "pays_destination", _country_label(*contextual["pays_destination_finale"]))

    if contextual["pays_provenance"]:
        tn_label = _country_label(*contextual["pays_provenance"])
        _set_field(data, "transport_international_nationalite", tn_label)
        _set_field(data, "transport_national_nationalite", tn_label)

    if contextual["pays_premiere_destination"]:
        _set_field(data, "importateur_pays", _country_label(*contextual["pays_premiere_destination"]))
