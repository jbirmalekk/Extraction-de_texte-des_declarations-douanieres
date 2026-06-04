"""Règles métier : vérification croisée uniquement après validation."""

from __future__ import annotations

from app.models.dum_document import DumDocument
from app.models.invoice import Invoice


def is_dum_validated(statut: str | None) -> bool:
    s = (statut or "").strip().lower()
    return s in ("validated", "valide")


def is_invoice_validated(statut: str | None) -> bool:
    s = (statut or "").strip().lower()
    return s in (
        "valide",
        "controle_croise",
        "controle_ok",
        "controle_warning",
        "controle_ecart",
    )


def assert_invoice_ready_for_compare(inv: Invoice) -> None:
    if not is_invoice_validated(inv.statut):
        raise ValueError(
            "La facture doit être validée avant la vérification croisée."
        )


def assert_dum_ready_for_compare(doc: DumDocument) -> None:
    if not is_dum_validated(doc.statut):
        raise ValueError(
            "La DUM doit être validée avant la vérification croisée."
        )
