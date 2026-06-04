"""Country codes used by OCR customs parsing."""

import re

COUNTRY_BY_CODE = {
    "TN": "TUNISIE",
    "DE": "ALLEMAGNE",
    "FR": "FRANCE",
    "IT": "ITALIE",
    "ES": "ESPAGNE",
    "BE": "BELGIQUE",
    "US": "USA",
    "CN": "CHINE",
    "TR": "TURQUIE",
    "NL": "PAYS BAS",
    "GB": "ROYAUME UNI",
}

COUNTRY_NAME_TO_CODE = {
    re.sub(r"\s+", " ", value).strip().upper(): code for code, value in COUNTRY_BY_CODE.items()
}
