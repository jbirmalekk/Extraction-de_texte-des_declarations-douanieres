import unittest

from app.services.ocr.article_row_extractor import (
    enrich_article_row_from_line,
    merge_cell_articles_with_regex_articles,
)
from app.services.parser_rules.customs_fallbacks import apply_customs_template_fallbacks
from app.services.parser_rules.customs_helpers import empty_result
from app.services.parser_rules.financial_fields import extract_financial_fields
from app.services.parser_rules.header_fields import extract_header_fields
from app.services.parser_rules.transport_fields import extract_transport_fields


class ParserRulesModuleTests(unittest.TestCase):
    def test_extract_header_fields_parses_core_header_values(self):
        data = empty_result()
        source = """
        TYPE DECLARATION IM4 3 120
        123456 01/02/2026
        """

        extract_header_fields(data, source)

        self.assertEqual(data.get("numero_declaration"), "123456")
        self.assertEqual(data.get("date_declaration"), "01-02-2026")
        self.assertEqual(data.get("type_declaration"), "IM4")
        self.assertEqual(data.get("nbre_articles"), "3")
        self.assertEqual(data.get("nombre_colis"), "120")

    def test_extract_transport_fields_parses_modes_and_conditions(self):
        data = empty_result()
        source = """
        TN 7 NAVIRE 14/03/2026
        TN 4 CAMION
        FOB 2 3
        """

        extract_transport_fields(data, source)

        self.assertEqual(data.get("transport_international_mode"), "7 - MARITIME")
        self.assertEqual(data.get("transport_national_mode"), "4 - ROUTIER")
        self.assertEqual(data.get("mode_livraison"), "FOB")
        self.assertEqual(data.get("mode_paiement"), "2")
        self.assertEqual(data.get("relation_acheteur_vendeur"), "3")
        self.assertEqual(data.get("date_arrivee_depart"), "14-03-2026")

    def test_extract_financial_fields_computes_fob_when_missing(self):
        data = empty_result()
        data["montant_ptfn"] = "1000.000"
        data["taux_conversion"] = "3.250000"

        extract_financial_fields(data, "Aucun montant de conversion explicite")

        self.assertEqual(data.get("valeur_fob_dt"), "3250.000")
        self.assertEqual(data.get("valeur_dinars"), "3250.000")
        self.assertEqual(data.get("valeur_totale"), "3250.000")

    def test_apply_customs_template_fallbacks_sets_critical_template_fields(self):
        data = empty_result()
        zones = {
            "tpl_importateur_nom": "RHINESTAHL CTS",
            "tpl_numero_declaration": "123456",
            "tpl_date_declaration": "05/05/2026",
            "tpl_type_declaration": "EA",
            "tpl_itineraire": "SFAX-RADES",
            "tpl_cle_authentification": "D505ABC1D",
        }

        parsed = apply_customs_template_fallbacks(data, "Texte OCR faible", zones_text=zones)

        self.assertEqual(parsed.get("importateur_nom"), "RHINESTAHL CTS")
        self.assertEqual(parsed.get("numero_declaration"), "123456")
        self.assertEqual(parsed.get("date_declaration"), "05-05-2026")
        self.assertEqual(parsed.get("type_declaration"), "EA")
        self.assertEqual(parsed.get("itineraire"), "SFAX-RADES")
        self.assertEqual(parsed.get("cle_authentification"), "D505ABC1D")

    def test_merge_cell_articles_keeps_page_and_fills_from_regex(self):
        cell = {
            "num_ligne": 1,
            "code_hs": "88073000011",
            "code_sh_ndp": "88073000011",
            "page": 1,
            "source": "table_cells",
            "poids_brut": "200",
        }
        regex = {
            "num_ligne": 1,
            "code_hs": "88073000011",
            "source": "regex",
            "poids_net": "104",
            "pfn": "11750.000",
        }
        merged = merge_cell_articles_with_regex_articles([cell], [regex])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["page"], 1)
        self.assertEqual(merged[0]["poids_brut"], "200")
        self.assertEqual(merged[0]["poids_net"], "104")
        self.assertEqual(merged[0]["pfn"], "11750.000")

    def test_enrich_article_row_from_line_extracts_qcs_pfn(self):
        line = (
            "1 88073000011 TN 39950.000 CODE QCS 06 QCS 104 PFN 11750.000 "
            "POIDS BRUT (KG) 200 POIDS NET (KG) 104"
        )
        row = enrich_article_row_from_line(line, page=2, code_hs="88073000011", num_ligne=1)
        self.assertEqual(row.get("page"), 2)
        self.assertEqual(row.get("qcs"), "104")
        self.assertEqual(row.get("pfn"), "11750.000")


if __name__ == "__main__":
    unittest.main()
