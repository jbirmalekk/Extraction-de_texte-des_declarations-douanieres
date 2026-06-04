import unittest

from app.services.parser_rules.customs_helpers import empty_result
from app.services.parser_rules.generic_party_extraction import apply_generic_parties_to_data


class GenericPartyExtractionTests(unittest.TestCase):
    def test_corrects_tn_provenance_when_de_pollution(self):
        data = empty_result()
        data["pays_provenance"] = "DE ALLEMAGNE"
        source = "PAYS DE PROVENANCE TN TUNISIE PAYS D ACHAT TN TUNISIE"
        apply_generic_parties_to_data(data, source)
        self.assertEqual(data.get("pays_provenance"), "TN TUNISIE")

    def test_rejects_exporter_bleed_in_importer(self):
        data = empty_result()
        data["importateur_nom"] = "5751 FAB EQUIPEMENTS ENGINEERING"
        source = """
        EXPORTATEUR 5751:FAB EQUIPEMENTS MECANIQUES ENGINEERING MACHINING PRECISION
        IMPORTATEUR CL 101 RHINESTAHL CTS USA
        """
        apply_generic_parties_to_data(data, source)
        self.assertIn("RHINESTAHL", str(data.get("importateur_nom") or "").upper())

    def test_importateur_reads_from_label_window_not_forced_cl101(self):
        data = empty_result()
        data["importateur_nom"] = "CL 104 OCR ERREUR"
        source = """
        IMPORTATEUR
        CL 104 ACME LOGISTICS INTERNATIONAL USA
        DECLARANT STE TRANSIT NORD
        """
        apply_generic_parties_to_data(data, source)
        imp = str(data.get("importateur_nom") or "").upper()
        self.assertIn("ACME", imp)
        self.assertNotEqual(imp, "CL101 RHINESTAHL CTS")

    def test_importateur_noise_sanitized_when_exporter_bleed(self):
        data = empty_result()
        data["importateur_nom"] = "5751 FAB EQUIPEMENTS ENGINEERING"
        source = """
        EXPORTATEUR 5751:FAB EQUIPEMENTS MECANIQUES
        IMPORTATEUR
        CL 88 SOCIETE GAMMA GMBH USA
        """
        apply_generic_parties_to_data(data, source)
        imp = str(data.get("importateur_nom") or "").upper()
        self.assertIn("GAMMA", imp)
        self.assertNotIn("FAB EQUIPEMENTS", imp)

    def test_pays_achat_follows_tn_provenance(self):
        data = empty_result()
        data["pays_provenance"] = "TN TUNISIE"
        data["pays_achat"] = "DE ALLEMAGNE"
        source = "PAYS DE PROVENANCE TN TUNISIE PAYS D ACHAT TN TUNISIE"
        apply_generic_parties_to_data(data, source)
        self.assertEqual(data.get("pays_achat"), "TN TUNISIE")

    def test_exportateur_from_label_window_reads_ocr_line(self):
        """Le nom vient du texte OCR dans EXPORTATEUR, sans fusion imposée FAB+ENGINEERING."""
        data = empty_result()
        data["exportateur_nom"] = "NADL BECLARATION GARBAGE"
        source = """
        EXPORTATEUR
        5751:FAB EQUIPEMENTS MECANIQUES ENGINEERING MACHINING PRECISION 1113819W
        IMPORTATEUR CL 101 RHINESTAHL CTS USA
        """
        apply_generic_parties_to_data(data, source)
        exp = str(data.get("exportateur_nom") or "").upper()
        self.assertIn("5751", exp)
        self.assertIn("FAB EQUIPEMENTS", exp)
        self.assertEqual(data.get("exportateur_code"), "1113819W")

    def test_declarant_neutral_not_forced_emp(self):
        data = empty_result()
        data["declarant_nom"] = "GARBAGE"
        source = """
        DECLARANT
        5051 STE MON COMMISSAIRE DOUANE TUNIS
        IMPORTATEUR ACME USA
        """
        apply_generic_parties_to_data(data, source)
        decl = str(data.get("declarant_nom") or "").upper()
        self.assertIn("COMMISSAIRE", decl)
        self.assertNotEqual(decl, "EMP")

    def test_exportateur_neutral_other_company(self):
        data = empty_result()
        data["exportateur_nom"] = "PORTATEUR POLLUTION"
        source = """
        EXPORTATEUR
        8842:ACME INDUSTRIE SARL MAROC
        IMPORTATEUR SOCIETE BETA INTERNATIONAL
        DECLARANT STE TRANSIT TUNIS
        """
        apply_generic_parties_to_data(data, source)
        exp = str(data.get("exportateur_nom") or "").upper()
        self.assertIn("ACME", exp)
        self.assertNotIn("EQUIPEMENTS MECANIQUES", exp)
        self.assertNotIn("ENGINEERING MACHINING", exp)


    def test_pick_best_party_line_prefers_code_colon_over_banner_noise(self):
        from app.services.parser_rules.generic_party_extraction import _pick_best_party_line

        noisy = (
            "NADL BECLARATION CERTIFICAT NUMERO DATE ENGINEERING MACHIN ING "
            "543108 14-11-2025 IMPORTATEUR HYDRO"
        )
        good = "5751:FAB EQUIPEMENTS MECANIQUES ENGINEERING MACHINING PRECISION"
        best = _pick_best_party_line([noisy, good], role="export")
        self.assertIn("5751", best or "")
        self.assertNotIn("CERTIFICAT", (best or "").upper())

    def test_strip_importateur_noise_keeps_gmbh(self):
        from app.services.parser_rules.customs_helpers import strip_importateur_ocr_noise

        raw = "PIAL ASAL YF YAO SHOW HYDRO SYSTEMS GMBH"
        out = strip_importateur_ocr_noise(raw)
        self.assertIn("HYDRO", out or "")
        self.assertIn("GMBH", out or "")
        self.assertNotIn("PIAL", out or "")

    def test_rejects_ocr_noise_exportateur(self):
        from app.services.parser_rules.customs_helpers import _looks_like_garbled_party_name

        self.assertTrue(
            _looks_like_garbled_party_name("SRUERYYYEEENMENR EEE EEE", role="export")
        )

    def test_importateur_bleed_cleared_and_foreign_export_recovered(self):
        data = empty_result()
        data["exportateur_nom"] = "SRUERYYYEEENMENR EEE EEE"
        data["importateur_nom"] = "=; 541 5751:FAB EQUIPEMENTS MECANIQUES"
        source = """
        EXPORTATEUR GEEVE HYDRAULICS B.V PAYS-BAS
        IMPORTATEUR 5751:FAB EQUIPEMENTS MECANIQUES ENGINEERING MACHINING PRECISION
        DECLARANT STE TRANSIT
        """
        apply_generic_parties_to_data(data, source)
        exp = str(data.get("exportateur_nom") or "").upper()
        imp = str(data.get("importateur_nom") or "").upper()
        self.assertIn("GEEVE", exp)
        self.assertIn("FAB", imp)
        self.assertNotIn("=;", imp)

    def test_sync_geeve_export_fab_import_layout(self):
        data = empty_result()
        data["exportateur_nom"] = "5751:FAB EQUIPEMENTS MECANIQUES"
        data["importateur_nom"] = "T RBA PRO TER GARBAGE"
        data["exportateur_code"] = "1113819W"
        source = """
        EXPORTATEUR GEEVE HYDRAULICS B.V PAYS-BAS
        IMPORTATEUR 5751:FAB EQUIPEMENTS MECANIQUES ENGINEERING MACHINING PRECISION 1113819W
        113 JAWDET ELHAYAT SOUKRA
        DECLARANT EMP SEKIT EDDEYER
        """
        apply_generic_parties_to_data(data, source)
        self.assertIn("GEEVE", str(data.get("exportateur_nom") or "").upper())
        self.assertIn("FAB", str(data.get("importateur_nom") or "").upper())
        self.assertEqual(str(data.get("code_importateur") or "").upper().replace(" ", ""), "1113819W")

    def test_sync_without_exportateur_label_importatewr_typo(self):
        """677329 : GEEVE présent mais libellé EXPORTATEUR illisible (IMPORTATEWR dans le crop)."""
        data = empty_result()
        data["exportateur_nom"] = "IMPORTATEWR 5 5751 FAB EQUIPEMENTS INEERING MACHINING PRECISION"
        data["importateur_nom"] = "5751:FAB EQUIPEMENTS MECANIQUES"
        data["exportateur_code"] = "11138190W"
        data["adresse_exportateur"] = "113 JAWDET ELHAYAT SOUKRA"
        source = """
        677329 20-05-2026 TYPE SA
        IMPORTATEWR 5 5751 FAB EQUIPEMENTS INEERING MACHINING PRECISION
        GEEVE HYDRAULICS B.V PAYS-BAS NL
        IMPORTATEUR 5751:FAB EQUIPEMENTS MECANIQUES ENGINEERING MACHINING PRECISION 1113819W
        113 JAWDET ELHAYAT SOUKRA
        DECLARANT ENGINEERING MACHINING PRECISION
        PAYS DE PROVENANCE NL PAYS BAS
        """
        apply_generic_parties_to_data(data, source)
        self.assertIn("GEEVE", str(data.get("exportateur_nom") or "").upper())
        self.assertIn("FAB", str(data.get("importateur_nom") or "").upper())
        self.assertNotIn("IMPORTATEWR", str(data.get("exportateur_nom") or "").upper())
        self.assertEqual(str(data.get("code_importateur") or "").upper().replace(" ", ""), "1113819W")
        self.assertIsNone(data.get("adresse_exportateur"))

    def test_cleanup_neutral_no_rhinestahl_injection(self):
        from app.services.parser_rules.customs_cleanup import apply_final_customs_cleanup

        data = {"importateur_nom": None, "importateur": None}
        apply_final_customs_cleanup(
            data,
            "IMPORTATEUR RHINESTAHL CTS USA DECLARANT STE SMART CUSTOMS",
        )
        self.assertIsNone(data.get("importateur_nom"))


if __name__ == "__main__":
    unittest.main()
