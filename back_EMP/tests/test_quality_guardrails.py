import unittest

from app.services.ocr.orchestrator import (
    _apply_quality_guardrails,
    _drop_polluted_identity_fields,
    _sanitize_noisy_geo_fields,
    _is_coherent_existing_value,
    _is_weak_candidate,
)


class QualityGuardrailsTests(unittest.TestCase):
    def test_marks_critical_fields_for_review_when_registration_quality_low(self):
        payload = {
            "registration_quality": {"score": 0.33, "quality": "LOW"},
            "zone_conflict_flags": [],
            "flags_validation": [],
            "numero_declaration": "123456",
            "date_declaration": "01-01-2026",
            "type_declaration": "EA",
            "exportateur_nom": "EXPORT CO",
            "importateur_nom": "IMPORT CO",
            "declarant_nom": "DECLARANT CO",
            "bureau_douane": "BR - SFAX",
            "cle_authentification": "D505ABC1D",
        }

        guarded = _apply_quality_guardrails(payload)

        self.assertEqual(guarded.get("numero_declaration"), "123456")
        self.assertEqual(guarded.get("date_declaration"), "01-01-2026")
        self.assertEqual(guarded.get("type_declaration"), "EA")
        self.assertEqual(guarded.get("exportateur_nom"), "EXPORT CO")
        self.assertEqual(guarded.get("importateur_nom"), "IMPORT CO")
        self.assertEqual(guarded.get("declarant_nom"), "DECLARANT CO")
        self.assertEqual(guarded.get("bureau_douane"), "BR - SFAX")
        self.assertEqual(guarded.get("cle_authentification"), "D505ABC1D")
        self.assertIn("critical_fields_manual_review_required", guarded.get("flags_validation", []))
        self.assertIn("critical_fields_needing_review", guarded)

    def test_does_not_block_when_quality_ok_and_no_conflicts(self):
        payload = {
            "registration_quality": {"score": 0.91, "quality": "HIGH"},
            "zone_conflict_flags": [],
            "flags_validation": [],
            "numero_declaration": "123456",
            "date_declaration": "01-01-2026",
            "type_declaration": "EA",
        }

        guarded = _apply_quality_guardrails(payload)

        self.assertEqual(guarded.get("numero_declaration"), "123456")
        self.assertEqual(guarded.get("date_declaration"), "01-01-2026")
        self.assertEqual(guarded.get("type_declaration"), "EA")
        self.assertNotIn("critical_fields_manual_review_required", guarded.get("flags_validation", []))
        self.assertNotIn("critical_fields_needing_review", guarded)

    def test_weak_candidate_detection_for_importer_pollution(self):
        self.assertTrue(_is_weak_candidate("importateur_nom", "DECLARANT CODE 7179"))
        self.assertFalse(_is_weak_candidate("importateur_nom", "HYDRO Systems GmbH"))

    def test_weak_candidate_detection_for_repertoire_shape(self):
        self.assertTrue(_is_weak_candidate("num_repertoire", "ABC12"))
        self.assertFalse(_is_weak_candidate("num_repertoire", "7207"))

    def test_coherent_existing_value_for_nombre_colis(self):
        self.assertTrue(_is_coherent_existing_value("nombre_colis", "1"))
        self.assertFalse(_is_coherent_existing_value("nombre_colis", "ABC"))

    def test_drop_polluted_identity_fields(self):
        payload = {
            "importateur_nom": "CLARANT - 7179 L R PERTOIRE",
            "importateur": "CLARANT - 7179 L R PERTOIRE",
            "declarant_nom": "STE SMART CUSTOMS BROKERS",
            "field_reject_reasons": [],
        }
        cleaned = _drop_polluted_identity_fields(payload)
        self.assertIsNone(cleaned.get("importateur_nom"))
        self.assertIsNone(cleaned.get("importateur"))
        self.assertEqual(cleaned.get("declarant_nom"), "STE SMART CUSTOMS BROKERS")
        self.assertIn("importateur_nom_rejected_label_pollution", cleaned.get("field_reject_reasons", []))

    def test_sanitize_noisy_country_and_itinerary(self):
        payload = {
            "pays_achat": "+=e oe eeveeawus",
            "pays_destination_finale": "Donieall_——ooo2 i ne,ity",
            "itineraire": "TC-OO",
            "field_reject_reasons": [],
        }
        cleaned = _sanitize_noisy_geo_fields(payload)
        self.assertIsNone(cleaned.get("pays_achat"))
        self.assertIsNone(cleaned.get("pays_destination_finale"))
        self.assertIn("pays_achat_rejected_unreadable_country", cleaned.get("field_reject_reasons", []))
        self.assertIn("pays_destination_finale_rejected_unreadable_country", cleaned.get("field_reject_reasons", []))


if __name__ == "__main__":
    unittest.main()
