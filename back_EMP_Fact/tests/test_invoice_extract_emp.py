"""Tests extraction facture EMP (template Export Invoice)."""

from app.services.invoice_extract import parse_invoice_text

SAMPLE_EMP = """
Export Invoice
Number FA2500287
Date 12/11/2025
FOR-COM-12/00/20/02/2019
uotes N°: DE2500528 /
Delivery / BL2500730

Belling Adress
CL252
HYDRO Systems GmbH & Co. KG
Ahfeldstrasse 10, 77781 Biberach/Baden Germany, Allemagne
Matricule Fiscal: DE256627297

Expedition Adress
Engineering & Machining Precision Route Mahdia, Sekiet Eddayer - Sfax, Tunisie

Delivery Adress
Hydro Systems GmbH & Co. KG Werk Biberach Ahfeldstrasse 10, 77781 BIBERACH/BADEN GERMANY

Reference Designation Qty Unit Price Amount
MUP_PWA211862 E BC N° : 4500318238 Manufacturing of a Storage stand 1,00 16 300,00 € 16 300,00 €
Transport fees for PWA211862 800,00 € 800,00 €

Gross 17 100,00 €
Discount 0,00 €
Amount 17 100,00 €
All Taxes Included 17 100,00 €
NET PAY 17 100,00 €

Package Number 1
PB in Kg 130,00
PN in Kg 57,00

Virement 30 Day(s)
* Incoterme : DAP. Seafreight. Port Rades.
"""


def test_emp_invoice_key_fields():
    out = parse_invoice_text(SAMPLE_EMP)
    assert out.numero_facture == "FA2500287"
    assert out.date_facture == "12/11/2025"
    assert out.net_pay == 17100.0
    assert out.montant_brut == 17100.0
    assert out.montant_remise == 0.0
    assert out.incoterm == "DAP"
    assert out.client_code == "CL252"
    assert "HYDRO" in (out.client_nom or "")
    assert out.nombre_colis == 1
    assert out.poids_brut_kg == 130.0
    assert len(out.lines) >= 2
    assert any(l.montant_ligne == 16300.0 for l in out.lines)
    assert any(l.montant_ligne == 800.0 for l in out.lines)


def test_totals_from_line_sum_fallback():
    """Sans tableau Gross visible, somme 16300+800 -> 17100."""
    text = """
    FA2500287
  16 300,00 €
    Transport fees 800,00 €
    PB in Kg 130,00
    """
    out = parse_invoice_text(text)
    assert out.net_pay == 17100.0
    assert out.montant_brut == 17100.0


def test_totals_not_confused_with_pb_weight():
    """Le poids PB 130 kg ne doit pas remplacer NET PAY / Gross."""
    ocr_like = SAMPLE_EMP + "\nPB in Kg 130,00\nPN in Kg 57,00\n"
    out = parse_invoice_text(ocr_like)
    assert out.net_pay == 17100.0
    assert out.montant_brut == 17100.0
    assert out.poids_brut_kg == 130.0
