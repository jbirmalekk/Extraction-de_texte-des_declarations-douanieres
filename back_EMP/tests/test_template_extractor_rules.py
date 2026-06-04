import unittest

from app.services.template_extractor import _extract_direct_fields


class TemplateExtractorRulesTests(unittest.TestCase):
    def test_exporter_name_and_address_are_separated(self):
        fields = _extract_direct_fields(
            {
                "exportateur_nom": "ENGINEERING MACHINING PRECISION",
                "adresse_exportateur": "113 JAWDET ELHAYAT SOUKRA",
            }
        )
        self.assertEqual(fields.get("exportateur_nom"), "ENGINEERING MACHINING PRECISION")
        self.assertEqual(fields.get("adresse_exportateur"), "113 JAWDET ELHAYAT SOUKRA")

    def test_rejects_exporter_name_with_address_pollution(self):
        fields = _extract_direct_fields(
            {
                "exportateur_nom": "EXPORTATEUR 113 JAWDET ELHAYAT SOUKRA",
            }
        )
        self.assertIsNone(fields.get("exportateur_nom"))
        self.assertIn("exportateur_nom_rejected_label_pollution", fields.get("field_reject_reasons", []))

    def test_importer_name_and_address_are_separated(self):
        fields = _extract_direct_fields(
            {
                "importateur_nom": "HYDRO Systems GmbH",
                "adresse_importateur": "77781 Biberach Germany",
            }
        )
        self.assertEqual(fields.get("importateur_nom"), "HYDRO SYSTEMS GMBH")
        self.assertEqual(fields.get("adresse_importateur"), "77781 BIBERACH GERMANY")

    def test_rejects_importer_address_if_it_is_entrepot_text(self):
        fields = _extract_direct_fields(
            {
                "adresse_importateur": "SUITE DIVERS SA- SEKIT EDDEYER SFAX",
            }
        )
        self.assertIsNone(fields.get("adresse_importateur"))
        self.assertIn("adresse_importateur_rejected_invalid_address", fields.get("field_reject_reasons", []))

    def test_rejects_importer_name_with_address_pollution(self):
        fields = _extract_direct_fields(
            {
                "importateur_nom": "IMPORTATEUR 77781 Biberach Germany",
            }
        )
        self.assertIsNone(fields.get("importateur_nom"))
        self.assertIn("importateur_nom_rejected_label_pollution", fields.get("field_reject_reasons", []))

    def test_rejects_importer_label_pollution(self):
        fields = _extract_direct_fields(
            {
                "importateur_nom": "CLARANT - 7179 L R PERTOIRE",
            }
        )
        self.assertNotEqual(fields.get("importateur_nom"), "CLARANT - 7179 L R PERTOIRE")
        self.assertIn("importateur_nom_rejected_label_pollution", fields.get("field_reject_reasons", []))

    def test_declarant_name_address_and_repertoire_are_separated(self):
        fields = _extract_direct_fields(
            {
                "declarant_nom": "EMP",
                "adresse_declarant": "SEKIT EDDEYER SFAX",
                "num_repertoire": "7207",
            }
        )
        self.assertEqual(fields.get("declarant_nom"), "EMP")
        self.assertEqual(fields.get("adresse_declarant"), "SEKIT EDDEYER SFAX")
        self.assertEqual(fields.get("num_repertoire"), "7207")

    def test_rejects_declarant_name_when_it_looks_like_address(self):
        fields = _extract_direct_fields(
            {
                "declarant_nom": "EN DE TRANSPORT DE",
            }
        )
        self.assertIsNone(fields.get("declarant_nom"))
        self.assertIn("declarant_nom_rejected_label_pollution", fields.get("field_reject_reasons", []))

    def test_prefers_labeled_nombre_colis_from_liquidation(self):
        fields = _extract_direct_fields(
            {
                "nombre_colis": "4",
                "block_liquidation": "Nbre colis 1",
            }
        )
        self.assertEqual(fields.get("nombre_colis"), "1")

    def test_recovers_repertoire_and_credit_from_declarant_block(self):
        fields = _extract_direct_fields(
            {
                "block_declarant": "Declarant 7179 Repertoire N° credit 5304740",
            }
        )
        self.assertEqual(fields.get("num_repertoire"), "7179")
        self.assertEqual(fields.get("numero_credit"), "5304740")

    def test_recovers_logistics_and_weights_from_text(self):
        fields = _extract_direct_fields(
            {
                "block_transport": "Bureau Frontiere 16 Destination 47 Localisation EXPORT",
                "block_article_1": "Poids brut 57 Poids net 57",
            }
        )
        self.assertEqual(fields.get("bureau_frontiere"), "16")
        self.assertEqual(fields.get("destination"), "47")
        self.assertEqual(fields.get("localisation_export"), "EXPORT")
        self.assertEqual(fields.get("poids_brut"), "57")
        self.assertEqual(fields.get("poids_net"), "57")

    def test_recovers_regime_triplet_from_table_block(self):
        fields = _extract_direct_fields(
            {
                "block_article_1": "Reglement financier 21 Code delai 22 Code OCI 4",
            }
        )
        self.assertEqual(fields.get("code_regime_financier"), "21")
        self.assertEqual(fields.get("code_delai"), "22")
        self.assertEqual(fields.get("code_oci"), "4")

    def test_guided_declarant_and_credit_mapping(self):
        fields = _extract_direct_fields(
            {
                "block_declarant": "Declarant ENGINEERING MACHINING PRECISION Repertoire 7132 N° credit 4806943",
            }
        )
        self.assertEqual(fields.get("declarant_nom"), "ENGINEERING MACHINING PRECISION")
        self.assertEqual(fields.get("num_repertoire"), "7132")
        self.assertEqual(fields.get("numero_credit"), "4806943")

    def test_guided_article_qcs_pfn_mapping(self):
        fields = _extract_direct_fields(
            {
                "block_article_1": "Code QCS 06 QCS 2400 PFN 249936.000",
            }
        )
        self.assertEqual(fields.get("code_qcs"), "06")
        self.assertEqual(fields.get("qcs"), "2400")
        self.assertEqual(fields.get("pfn"), "249936.000")

    def test_rejects_noisy_declarant_block_text(self):
        fields = _extract_direct_fields(
            {
                "block_declarant": "TYPE DECLARATION SI SNP TOTAL C EA 1 4 REGIME FINANCIER",
            }
        )
        self.assertIsNone(fields.get("declarant_nom"))

    def test_rejects_tiny_weight_noise(self):
        fields = _extract_direct_fields(
            {
                "block_article_1": "Poids brut 3 Poids net 3",
            }
        )
        self.assertIsNone(fields.get("poids_brut"))
        self.assertIsNone(fields.get("poids_net"))

    def test_guided_country_fields_from_labels(self):
        fields = _extract_direct_fields(
            {
                "block_conditions": (
                    "Pays de provenance DE ALLEMAGNE "
                    "Pays d'achat TN TUNISIE "
                    "Pays premiere destination US USA "
                    "Pays destination definitive FR FRANCE"
                ),
            }
        )
        self.assertEqual(fields.get("pays_provenance"), "DE ALLEMAGNE")
        self.assertEqual(fields.get("pays_achat"), "TN TUNISIE")
        self.assertEqual(fields.get("pays_premiere_destination"), "US USA")
        self.assertEqual(fields.get("pays_destination_finale"), "FR FRANCE")
        self.assertEqual(fields.get("pays_destination"), "FR FRANCE")

    def test_phase_c_two_pass_anchor_declarant_credit_repertoire(self):
        fields = _extract_direct_fields(
            {
                "block_declarant": (
                    "Some noise before\n"
                    "DECLARANT\n"
                    "AEROSPACE CUSTOMS SERVICES\n"
                    "N° CREDIT\n"
                    "5304740\n"
                    "REPERTOIRE\n"
                    "7179\n"
                    "MOYEN DE TRANSPORT"
                ),
            }
        )
        self.assertEqual(fields.get("declarant_nom"), "AEROSPACE CUSTOMS SERVICES")
        self.assertEqual(fields.get("numero_credit"), "5304740")
        self.assertEqual(fields.get("num_repertoire"), "7179")

    def test_phase_c_two_pass_anchor_logistics_split_lines(self):
        fields = _extract_direct_fields(
            {
                "block_transport": (
                    "BUREAU FRONTIERE\n"
                    "16\n"
                    "DESTINATION\n"
                    "47\n"
                    "LOCALISATION\n"
                    "EXPORT"
                ),
            }
        )
        self.assertEqual(fields.get("bureau_frontiere"), "16")
        self.assertEqual(fields.get("destination"), "47")
        self.assertEqual(fields.get("localisation_export"), "EXPORT")


if __name__ == "__main__":
    unittest.main()
