import unittest

from app.services.parser_v2 import parse_fields, valider_champs


class ParserV2Tests(unittest.TestCase):
    def test_valider_champs_sets_quality_fields(self):
        payload = {
            "numero_declaration": "123456",
            "date_declaration": "01/01/2026",
            "type_declaration": "DAE",
            "devise": "EUR",
            "exportateur_nom": "EXPORT COMPANY",
            "importateur_nom": "IMPORT COMPANY",
            "poids_brut": "100",
            "poids_net": "90",
            "bureau_douane": "BR ARIANA",
            "cle_authentification": "D505ABC1D",
        }

        validated = valider_champs(payload)
        self.assertIn("score_confiance", validated)
        self.assertIn("flags_validation", validated)
        self.assertIn("qualite", validated)
        self.assertIsInstance(validated["flags_validation"], list)
        self.assertGreaterEqual(validated["score_confiance"], 0)
        self.assertLessEqual(validated["score_confiance"], 100)

    def test_parse_fields_returns_expected_structure(self):
        sample_text = """
        NUMERO DECLARATION 123456
        DATE 01/01/2026
        TYPE DAE
        EXPORTATEUR EXPORT COMPANY
        IMPORTATEUR IMPORT COMPANY
        BUREAU BR ARIANA
        """
        parsed = parse_fields(sample_text)
        required_keys = {
            "numero_declaration",
            "date_declaration",
            "type_declaration",
            "taxes",
            "articles",
            "score_confiance",
            "qualite",
            "flags_validation",
        }
        for key in required_keys:
            self.assertIn(key, parsed)
        self.assertIsInstance(parsed["taxes"], list)
        self.assertIsInstance(parsed["articles"], list)

    def test_template_fallback_importer_and_route(self):
        parsed = parse_fields(
            "Texte OCR partiel",
            zones_text={
                "tpl_importateur_nom": "RHINESTAHL CTS",
                "tpl_itineraire": "SFAX-RADES",
                "tpl_cle_authentification": "D505ABC1D",
            },
        )
        self.assertEqual(parsed.get("importateur_nom"), "RHINESTAHL CTS")
        self.assertEqual(parsed.get("itineraire"), "SFAX-RADES")
        self.assertEqual(parsed.get("cle_authentification"), "D505ABC1D")

    def test_weight_consistency_flag_when_invalid(self):
        payload = {
            "numero_declaration": "123456",
            "date_declaration": "01/01/2026",
            "type_declaration": "DAE",
            "exportateur_nom": "EXPORT COMPANY",
            "importateur_nom": "IMPORT COMPANY",
            "poids_brut": "10",
            "poids_net": "50",
            "bureau_douane": "BR ARIANA",
            "cle_authentification": "D505ABC1D",
        }
        validated = valider_champs(payload)
        self.assertIn("poids_brut_>=_poids_net", validated.get("flags_validation", []))


if __name__ == "__main__":
    unittest.main()
