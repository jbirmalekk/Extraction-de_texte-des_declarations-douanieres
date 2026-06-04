"""Canonical field schema used by template extractor."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldZone:
    name: str
    y1: float
    y2: float
    x1: float
    x2: float
    psm: int
    isolated: bool = True

    @property
    def ratio(self) -> tuple[float, float, float, float]:
        return (self.y1, self.y2, self.x1, self.x2)


# Micro-zones bandeau « Informations générales » (partie 6 — OCR par cellule).
HEADER_CELL_ZONES: tuple[FieldZone, ...] = (
    FieldZone("exportateur_nom", 0.070, 0.095, 0.148, 0.438, 6),
    FieldZone("adresse_exportateur", 0.091, 0.105, 0.148, 0.438, 7),
    FieldZone("exportateur_code", 0.106, 0.117, 0.428, 0.508, 7),
    FieldZone("code_importateur", 0.120, 0.138, 0.148, 0.228, 7),
    FieldZone("importateur_nom", 0.120, 0.148, 0.228, 0.405, 6),
    FieldZone("importateur_pays_cell", 0.120, 0.148, 0.405, 0.498, 6),
    FieldZone("adresse_entreposage", 0.108, 0.134, 0.528, 0.858, 6),
    FieldZone("declarant_code", 0.152, 0.164, 0.218, 0.312, 7),
    FieldZone("declarant_nom", 0.168, 0.196, 0.148, 0.488, 7),
    FieldZone("pays_provenance", 0.154, 0.178, 0.545, 0.728, 6),
    FieldZone("pays_achat", 0.154, 0.178, 0.748, 0.928, 6),
    FieldZone("pays_premiere_destination", 0.183, 0.216, 0.545, 0.728, 6),
    FieldZone("pays_destination_finale", 0.183, 0.216, 0.768, 0.928, 6),
)

FIELD_ZONES: tuple[FieldZone, ...] = (
    # DUM TTN : colonne gauche x≈0.14–0.50 ; pays encadrés 15–18 souvent y≈0.155–0.22 et x>0.54.
    FieldZone("exportateur_area", 0.048, 0.102, 0.138, 0.438, 6, isolated=False),
    # Raison sociale — case 2 uniquement (exclut n° déclaration / importateur).
    FieldZone("exportateur_nom", 0.070, 0.095, 0.148, 0.438, 6),
    FieldZone("adresse_exportateur", 0.091, 0.108, 0.148, 0.438, 7),
    FieldZone("numero_declaration", 0.050, 0.078, 0.512, 0.615, 7),
    FieldZone("date_declaration", 0.050, 0.078, 0.618, 0.720, 7),
    FieldZone("type_declaration", 0.096, 0.120, 0.730, 0.766, 7),
    FieldZone("nbre_articles", 0.096, 0.120, 0.783, 0.828, 7),
    FieldZone("nombre_colis", 0.099, 0.118, 0.874, 0.902, 7),
    FieldZone("exportateur_code", 0.107, 0.116, 0.420, 0.512, 7),
    FieldZone("code_importateur", 0.120, 0.138, 0.148, 0.228, 7),
    FieldZone("importateur_nom", 0.120, 0.148, 0.228, 0.405, 6),
    FieldZone("adresse_importateur", 0.146, 0.168, 0.148, 0.498, 6, isolated=False),
    FieldZone("adresse_entreposage", 0.108, 0.134, 0.528, 0.858, 6, isolated=False),
    FieldZone("declarant_code", 0.152, 0.164, 0.218, 0.318, 7),
    FieldZone("num_repertoire", 0.150, 0.164, 0.322, 0.448, 7),
    FieldZone("declarant_nom", 0.168, 0.196, 0.148, 0.488, 7),
    FieldZone("adresse_declarant", 0.194, 0.218, 0.142, 0.498, 6, isolated=False),
    FieldZone("pays_provenance", 0.154, 0.178, 0.545, 0.728, 6),
    FieldZone("pays_achat", 0.154, 0.178, 0.748, 0.928, 6),
    FieldZone("pays_premiere_destination", 0.183, 0.216, 0.545, 0.728, 6),
    FieldZone("pays_destination_finale", 0.183, 0.216, 0.768, 0.928, 6),
    FieldZone("block_transport", 0.206, 0.265, 0.150, 0.475, 6, isolated=False),
    FieldZone("block_conditions", 0.175, 0.288, 0.505, 0.920, 6, isolated=False),
    FieldZone("bureau_frontiere", 0.283, 0.306, 0.150, 0.240, 7),
    FieldZone("destination", 0.283, 0.306, 0.240, 0.335, 7),
    FieldZone("block_finances", 0.285, 0.325, 0.500, 0.900, 6, isolated=False),
    FieldZone("poids_brut", 0.378, 0.402, 0.505, 0.585, 7),
    FieldZone("poids_net", 0.378, 0.402, 0.588, 0.668, 7),
    FieldZone("engagement_date", 0.298, 0.322, 0.355, 0.485, 7),
    FieldZone("qualite_fiscale", 0.383, 0.407, 0.812, 0.913, 7),
    FieldZone("code_regime_financier", 0.446, 0.463, 0.538, 0.585, 7),
    FieldZone("code_delai", 0.446, 0.463, 0.625, 0.667, 7),
    # Case 47–48 Régime (à droite de C.Délai, avant QCI) | 49 FOB / Douane | 50 Coef.
    FieldZone("regime", 0.415, 0.448, 0.748, 0.838, 7),
    FieldZone("valeur_fob", 0.455, 0.492, 0.488, 0.598, 7),
    FieldZone("douane", 0.455, 0.492, 0.592, 0.708, 7),
    FieldZone("coefficient_ajustement", 0.462, 0.498, 0.748, 0.908, 7),
    FieldZone("block_article_1", 0.315, 0.475, 0.495, 0.912, 6, isolated=False),
    FieldZone("code_titre_ce_cell", 0.412, 0.442, 0.672, 0.752, 7),
    FieldZone("numero_titre_ce_cell", 0.412, 0.442, 0.758, 0.902, 7),
    FieldZone("texte_engagement_roi", 0.798, 0.942, 0.592, 0.908, 6, isolated=False),
    FieldZone("block_liquidation", 0.755, 0.973, 0.140, 0.915, 6, isolated=False),
)


def _overlap(a: FieldZone, b: FieldZone) -> bool:
    return (a.x1 < b.x2 and a.x2 > b.x1 and a.y1 < b.y2 and a.y2 > b.y1)


def validate_isolated_non_overlap() -> list[tuple[str, str]]:
    isolated = [zone for zone in FIELD_ZONES if zone.isolated]
    conflicts: list[tuple[str, str]] = []
    for i, left in enumerate(isolated):
        for right in isolated[i + 1 :]:
            if _overlap(left, right):
                conflicts.append((left.name, right.name))
    return conflicts
