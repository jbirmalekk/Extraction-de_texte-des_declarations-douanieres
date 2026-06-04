from app.schemas.invoice import CompareDumBody
from app.services.dum_lookup import document_to_compare_body, merge_compare_body, parse_amount


class FakeDum:
    numero_declaration = "FR-2024-001"
    devise = "EUR"
    montant_ptfn = "17100.000"
    nombre_colis = "1"
    poids_net = "57"
    mode_livraison = "DAP"


class FakeInv:
    dum_document_id = 42


def test_parse_amount():
    assert parse_amount("17 100,00") == 17100.0
    assert parse_amount("17100.000") == 17100.0


def test_document_to_compare_body():
    body = document_to_compare_body(FakeDum())
    assert body.montant_pfn_dum == 17100.0
    assert body.devise_dum == "EUR"
    assert body.numero_declaration_dum == "FR-2024-001"
    assert body.nombre_colis_dum == 1


class FakeSession:
    def get(self, _model, doc_id):
        if doc_id == 42:
            return FakeDum()
        return None


def test_merge_compare_body_from_linked_dum():
    inv = FakeInv()
    body = CompareDumBody(tolerance_abs=0.01)
    merged = merge_compare_body(FakeSession(), inv, body)
    assert merged.montant_pfn_dum == 17100.0
    assert merged.devise_dum == "EUR"
