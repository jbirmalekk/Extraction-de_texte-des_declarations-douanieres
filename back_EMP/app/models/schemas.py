from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── Ce que l'API retourne après OCR ──────────────────────────
class TaxeSchema(BaseModel):
    code      : Optional[str] = None
    assiette  : Optional[str] = None
    quotite   : Optional[str] = None
    montant   : Optional[str] = None


class ArticleSchema(BaseModel):
    num_ligne    : Optional[int]   = None
    code_hs      : Optional[str]   = None
    designation  : Optional[str]   = None
    quantite     : Optional[float] = None
    unite        : Optional[str]   = None
    prix_unitaire: Optional[float] = None
    total_ligne  : Optional[float] = None


class OCRResultSchema(BaseModel):
    # Identification
    numero_declaration       : Optional[str] = None
    date_declaration         : Optional[str] = None
    type_declaration         : Optional[str] = None
    nbre_articles            : Optional[str] = None

    # Exportateur
    exportateur_nom          : Optional[str] = None
    exportateur_code         : Optional[str] = None

    # Importateur
    importateur_nom          : Optional[str] = None
    importateur_pays         : Optional[str] = None

    # Déclarant
    declarant_code           : Optional[str] = None
    declarant_nom            : Optional[str] = None

    # Transport
    mode_transport           : Optional[str] = None
    date_arrivee_depart      : Optional[str] = None
    pays_provenance          : Optional[str] = None
    pays_destination         : Optional[str] = None
    adresse_entreposage      : Optional[str] = None

    # Finances
    mode_livraison           : Optional[str] = None
    devise                   : Optional[str] = None
    montant_ptfn             : Optional[str] = None
    valeur_fob_dt            : Optional[str] = None
    taux_conversion          : Optional[str] = None

    # Marchandises
    designation_marchandises : Optional[str] = None
    poids_brut               : Optional[str] = None
    poids_net                : Optional[str] = None

    # Listes
    taxes    : List[TaxeSchema]   = []
    articles : List[ArticleSchema] = []

    # Liquidation
    bureau_douane            : Optional[str] = None
    code_gdt                 : Optional[str] = None
    montant_liquidation      : Optional[str] = None
    itineraire               : Optional[str] = None
    num_agrement             : Optional[str] = None
    num_repertoire           : Optional[str] = None
    cle_authentification     : Optional[str] = None

    # Qualité OCR
    score_confiance          : Optional[int] = None
    qualite                  : Optional[str] = None
    flags_validation         : List[str]     = []

    # Métadonnées
    fichier                  : Optional[str] = None
    nb_cellules              : Optional[int] = None


# ── Ce que l'utilisateur envoie pour valider/corriger ────────
class OCRValidationSchema(BaseModel):
    document_id              : int
    numero_declaration       : Optional[str] = None
    date_declaration         : Optional[str] = None
    type_declaration         : Optional[str] = None
    exportateur_nom          : Optional[str] = None
    importateur_nom          : Optional[str] = None
    importateur_pays         : Optional[str] = None
    mode_transport           : Optional[str] = None
    devise                   : Optional[str] = None
    montant_ptfn             : Optional[str] = None
    valeur_fob_dt            : Optional[str] = None
    bureau_douane            : Optional[str] = None
    montant_liquidation      : Optional[str] = None
    statut                   : Optional[str] = "valide"


# ── Réponse de l'API après sauvegarde ────────────────────────
class DocumentResponseSchema(BaseModel):
    id                       : int
    fichier                  : Optional[str] = None
    numero_declaration       : Optional[str] = None
    date_declaration         : Optional[str] = None
    statut                   : Optional[str] = None
    score_confiance          : Optional[int] = None
    qualite                  : Optional[str] = None
    created_at               : Optional[datetime] = None

    class Config:
        from_attributes = True