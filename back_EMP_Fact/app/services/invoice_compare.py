"""Comparaison facture ↔ DUM (NET PAY vs PFN article)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.invoice import Invoice
from app.schemas.invoice import CompareDumBody, DumAnomalyOut


@dataclass
class CompareResult:
    ecart_montant: float
    ecart_commentaire: str
    statut_controle: str  # ok | warning | error
    anomalies: list[DumAnomalyOut] = field(default_factory=list)


def _parse_optional_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def compare_invoice_with_dum(inv: Invoice, body: CompareDumBody) -> CompareResult:
    """Compare NET PAY facture au PFN / montant PTFN de la DUM (même devise attendue)."""
    base = inv.net_pay if inv.net_pay is not None else inv.montant_ttc
    pfn_dum = body.montant_pfn_dum
    if pfn_dum is None and body.montant_declare_dum is not None:
        pfn_dum = body.montant_declare_dum

    anomalies: list[DumAnomalyOut] = []

    if base is None:
        anomalies.append(
            DumAnomalyOut(
                code="invoice_amount_missing",
                severity="error",
                message="Aucun NET PAY (ni TTC) sur la facture pour comparer.",
                facture_value=None,
                dum_value=str(pfn_dum) if pfn_dum is not None else None,
            )
        )
        return CompareResult(
            ecart_montant=0.0,
            ecart_commentaire="Montant facture manquant",
            statut_controle="error",
            anomalies=anomalies,
        )

    if pfn_dum is None:
        anomalies.append(
            DumAnomalyOut(
                code="dum_pfn_missing",
                severity="error",
                message="PFN article / montant PTFN DUM non fourni.",
                facture_value=str(base),
                dum_value=None,
            )
        )
        return CompareResult(
            ecart_montant=0.0,
            ecart_commentaire="Montant DUM manquant",
            statut_controle="error",
            anomalies=anomalies,
        )

    ecart = round(float(base) - float(pfn_dum), 4)
    dev_f = (inv.devise or "").upper().strip()
    dev_d = (body.devise_dum or body.devise_declaree_dum or "").upper().strip()

    statut = "ok"
    comment = "OK — NET PAY facture aligné avec PFN article DUM (tolérance respectée)."

    if dev_d and dev_f and dev_f != dev_d:
        statut = "warning"
        comment = f"Devises différentes : facture={dev_f}, DUM={dev_d} — vérifiez la comparaison."
        anomalies.append(
            DumAnomalyOut(
                code="currency_mismatch",
                severity="warning",
                message=comment,
                facture_value=dev_f,
                dum_value=dev_d,
            )
        )

    tol = float(body.tolerance_abs or 0.01)
    anomalies.append(
        DumAnomalyOut(
            code="montant_net_pay_vs_pfn",
            severity="info",
            message="Comparaison principale : NET PAY (facture) vs PFN article (DUM).",
            facture_value=f"{base} {dev_f}".strip(),
            dum_value=f"{pfn_dum} {dev_d}".strip(),
        )
    )

    if abs(ecart) > tol:
        sev = "error" if abs(ecart) > max(tol * 10, 1.0) else "warning"
        statut = "error" if sev == "error" else (statut if statut == "error" else "warning")
        comment = f"Écart montant {ecart:+.4f} (facture − DUM PFN)."
        anomalies.append(
            DumAnomalyOut(
                code="amount_gap",
                severity=sev,
                message=comment,
                facture_value=str(base),
                dum_value=str(pfn_dum),
            )
        )
    elif statut == "ok":
        anomalies.append(
            DumAnomalyOut(
                code="amount_ok",
                severity="info",
                message=f"Écart {ecart:+.4f} dans la tolérance ±{tol}.",
                facture_value=str(base),
                dum_value=str(pfn_dum),
            )
        )

    # Contrôles secondaires (informatifs)
    if body.nombre_colis_dum is not None and inv.nombre_colis is not None:
        if int(inv.nombre_colis) != int(body.nombre_colis_dum):
            anomalies.append(
                DumAnomalyOut(
                    code="colis_mismatch",
                    severity="warning",
                    message="Nombre de colis différent.",
                    facture_value=str(inv.nombre_colis),
                    dum_value=str(body.nombre_colis_dum),
                )
            )
            if statut == "ok":
                statut = "warning"

    pn_inv = _parse_optional_float(inv.poids_net_kg)
    pn_dum = _parse_optional_float(body.poids_net_kg_dum)
    if pn_inv is not None and pn_dum is not None and abs(pn_inv - pn_dum) > 0.5:
        anomalies.append(
            DumAnomalyOut(
                code="poids_net_mismatch",
                severity="warning",
                message="Poids net (kg) différent.",
                facture_value=str(pn_inv),
                dum_value=str(pn_dum),
            )
        )
        if statut == "ok":
            statut = "warning"

    if body.incoterm_dum and inv.incoterm:
        inc_f = inv.incoterm.upper().strip()[:3]
        inc_d = body.incoterm_dum.upper().strip()[:3]
        if inc_f != inc_d:
            anomalies.append(
                DumAnomalyOut(
                    code="incoterm_mismatch",
                    severity="warning",
                    message="Incoterm / mode livraison différent.",
                    facture_value=inc_f,
                    dum_value=inc_d,
                )
            )
            if statut == "ok":
                statut = "warning"

    if body.numero_declaration_dum and body.numero_declaration_dum.strip():
        anomalies.append(
            DumAnomalyOut(
                code="declaration_linked",
                severity="info",
                message=f"Déclaration DUM n° {body.numero_declaration_dum.strip()}.",
                facture_value=None,
                dum_value=body.numero_declaration_dum.strip(),
            )
        )

    return CompareResult(
        ecart_montant=ecart,
        ecart_commentaire=comment,
        statut_controle=statut,
        anomalies=anomalies,
    )
