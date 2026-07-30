"""Tests référentiel importateur."""

import unittest

from app.services.parser_rules.party_referential import (
    apply_party_referential_validation,
    lookup_importateur_name,
    normalize_importateur_code,
)


class PartyReferentialTests(unittest.TestCase):
    def test_normalize_cl_code(self):
        self.assertEqual(normalize_importateur_code("CL 101"), "CL101")
        self.assertEqual(normalize_importateur_code("cl101"), "CL101")

    def test_lookup_known_code(self):
        name = lookup_importateur_name("CL101")
        self.assertIsNotNone(name)
        self.assertIn("RHINESTAHL", name)

    def test_mismatch_only_flags_never_overwrites(self):
        # Consultatif : la valeur OCR ne doit JAMAIS être écrasée (aucun forçage).
        data = {
            "code_importateur": "CL101",
            "importateur_nom": "HYDRO SYSTEMS GMBH",
            "importateur": "HYDRO SYSTEMS GMBH",
        }
        out = apply_party_referential_validation(data)
        self.assertEqual(out.get("importateur_nom"), "HYDRO SYSTEMS GMBH")
        self.assertEqual(out.get("importateur"), "HYDRO SYSTEMS GMBH")
        self.assertIn("importateur_referential_mismatch", out.get("flags_validation", []))

    def test_empty_importateur_not_filled(self):
        # Consultatif : un champ vide reste vide, on signale seulement l'existence d'une référence.
        data = {"code_importateur": "CL101"}
        out = apply_party_referential_validation(data)
        self.assertFalse(out.get("importateur_nom"))
        self.assertIn("importateur_referential_hint_available", out.get("flags_validation", []))


if __name__ == "__main__":
    unittest.main()
