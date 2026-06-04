import unittest

from app.services.parser_v2 import parse_fields


class ExtractionNonRegressionTests(unittest.TestCase):
    def test_critical_fields_non_regression_from_template_and_text(self):
        text = """
        123456 01/01/2026
        TYPE DECLARATION EA 1 10
        TN 7 NAVIRE 01/01/2026
        RHINESTAHL CTS
        BR - SFAX
        D505ABC1D
        """
        zones_text = {
            "tpl_importateur_nom": "RHINESTAHL CTS",
            "tpl_numero_declaration": "123456",
            "tpl_date_declaration": "01/01/2026",
            "tpl_type_declaration": "EA",
            "tpl_itineraire": "SFAX-RADES",
            "tpl_bureau_douane": "BR - SFAX",
            "tpl_cle_authentification": "D505ABC1D",
        }

        parsed = parse_fields(text, zones_text=zones_text)

        self.assertEqual(parsed.get("numero_declaration"), "123456")
        self.assertEqual(parsed.get("date_declaration"), "01-01-2026")
        self.assertEqual(parsed.get("type_declaration"), "EA")
        self.assertEqual(parsed.get("importateur_nom"), "RHINESTAHL CTS")
        self.assertEqual(parsed.get("bureau_douane"), "BR - SFAX")
        self.assertEqual(parsed.get("itineraire"), "SFAX-RADES")
        self.assertEqual(parsed.get("cle_authentification"), "D505ABC1D")
        self.assertIn("score_confiance", parsed)
        self.assertIn("flags_validation", parsed)
        self.assertIn("qualite", parsed)


if __name__ == "__main__":
    unittest.main()
