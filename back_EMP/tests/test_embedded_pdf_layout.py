"""Tests parseur layout PDF douane à texte embarqué."""

import unittest
from pathlib import Path

from app.services.parser_rules.embedded_pdf_layout import (
    apply_embedded_pdf_layout,
    parse_embedded_pdf_layout,
)

SAMPLE = Path(__file__).resolve().parents[1] / "evaluation" / "sa677329_text_sample.txt"


class EmbeddedPdfLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SAMPLE.read_text(encoding="utf-8")

    def test_label_driven_selectable_pdf_text(self):
        text = """
Exportateur
GEISLER
USA
Importateur
ENGINEERING MACHIN ING PRECISION
113 JAWDET ELHAYAT SOUKRA
Déclarant
ENGINEERING MACHIN ING PRECISION
113 JAWDET ELHAYAT SOUKRA
SEKIT EDDEYER SFAX
Pays de provenance
US
U.S.A
Pays d'achat
TN
TUNISIE
Pays de première destination
US
U.S.A
Pays de destination définitive
TN
TUNISIE
"""
        out = parse_embedded_pdf_layout(text)
        self.assertEqual(out.get("exportateur_nom"), "GEISLER")
        self.assertEqual(out.get("importateur_nom"), "ENGINEERING MACHIN ING PRECISION")
        self.assertEqual(out.get("declarant_nom"), "ENGINEERING MACHIN ING PRECISION")
        self.assertEqual(out.get("pays_provenance"), "US USA")
        self.assertEqual(out.get("pays_achat"), "TN TUNISIE")
        self.assertEqual(out.get("pays_premiere_destination"), "US USA")
        self.assertEqual(out.get("pays_destination_finale"), "TN TUNISIE")

    def test_party_and_identification_block(self):
        out = parse_embedded_pdf_layout(self.text)
        self.assertEqual(out.get("importateur_nom"), "GEISLER")
        self.assertEqual(out.get("exportateur_nom"), "FAB EQUIPEMENTS MECANIQUES")
        self.assertEqual(out.get("code_exportateur"), "5751")
        self.assertEqual(out.get("numero_declaration"), "8056")
        self.assertEqual(out.get("numero_dae"), "679925")
        self.assertEqual(out.get("type_declaration"), "SA")
        self.assertEqual(out.get("pays_provenance"), "TN TUNISIE")
        self.assertEqual(out.get("pays_achat"), "US USA")
        self.assertEqual(out.get("pays_destination_finale"), "US USA")

    def test_article_and_footer(self):
        out = parse_embedded_pdf_layout(self.text)
        self.assertEqual(out.get("code_sh_ndp"), "73181520001")
        self.assertIn("VIS ET BOULONS", out.get("designation_marchandises", "").upper())
        self.assertEqual(out.get("cle_authentification"), "D798DDM1W")
        self.assertEqual(out.get("montant_liquidation"), "13.000")

    def test_apply_overrides_generic_pollution(self):
        polluted = {
            "exportateur_nom": "= PAL! DECLARATION NUMÉRO 2!",
            "importateur_nom": "5751:FAB EQUIPEMENTS MECANIQUES",
            "numero_declaration": "679925",
            "type_declaration": "SE",
        }
        out = apply_embedded_pdf_layout(polluted, self.text)
        self.assertEqual(out["exportateur_nom"], "FAB EQUIPEMENTS MECANIQUES")
        self.assertEqual(out["importateur_nom"], "GEISLER")
        self.assertEqual(out["numero_declaration"], "8056")
        self.assertEqual(out["type_declaration"], "SA")


if __name__ == "__main__":
    unittest.main()
