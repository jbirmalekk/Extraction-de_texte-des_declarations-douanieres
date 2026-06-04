import unittest

from app.services.parser_rules.article_value_fields import extract_article_value_fields
from app.services.parser_rules.customs_helpers import empty_result


class ArticleValueFieldsTests(unittest.TestCase):
    def test_extract_fob_douane_pair(self):
        data = empty_result()
        source = "VALEUR EN DINARS FOB 58477.725 DOUANE 58477.725 COEF AJUSTEMENT"
        extract_article_value_fields(data, source)
        self.assertEqual(data.get("valeur_fob"), "58477.725")
        self.assertEqual(data.get("douane"), "58477.725")
        self.assertEqual(data.get("valeur_fob_dt"), "58477.725")

    def test_extract_regime(self):
        data = empty_result()
        extract_article_value_fields(data, "REGIME 56 QCI")
        self.assertEqual(data.get("regime"), "56")

    def test_regime_not_confused_with_qualite_fiscale(self):
        data = empty_result()
        data["regime"] = "1"
        data["qualite_fiscale"] = "1"
        extract_article_value_fields(
            data,
            "POIDS NET 57 REGIME 56 FOB 58477.725 DOUANE 58477.725",
        )
        self.assertEqual(data.get("regime"), "56")


if __name__ == "__main__":
    unittest.main()
