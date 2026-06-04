"""Tests comparaison facture ↔ DUM (NET PAY vs PFN)."""

from app.models.invoice import Invoice
from app.schemas.invoice import CompareDumBody
from app.services.invoice_compare import compare_invoice_with_dum


def test_compare_ok_same_amount():
    inv = Invoice(net_pay=2600.0, devise="USD")
    body = CompareDumBody(montant_pfn_dum=2600.0, devise_dum="USD", tolerance_abs=0.01)
    result = compare_invoice_with_dum(inv, body)
    assert result.statut_controle == "ok"
    assert abs(result.ecart_montant) <= 0.01


def test_compare_gap_detected():
    inv = Invoice(net_pay=17100.0, devise="EUR")
    body = CompareDumBody(montant_pfn_dum=2600.0, devise_dum="USD", tolerance_abs=0.01)
    result = compare_invoice_with_dum(inv, body)
    assert result.statut_controle in ("warning", "error")
    assert result.ecart_montant == 14500.0


def test_compare_currency_warning():
    inv = Invoice(net_pay=100.0, devise="EUR")
    body = CompareDumBody(montant_pfn_dum=100.0, devise_dum="USD", tolerance_abs=0.01)
    result = compare_invoice_with_dum(inv, body)
    assert any(a.code == "currency_mismatch" for a in result.anomalies)
