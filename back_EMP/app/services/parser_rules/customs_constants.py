"""Shared constants for customs/template extraction."""

FORM_CASE_NUMBERS = {
    "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15",
    "16", "17", "18", "19", "20", "21", "22", "23", "24",
    "30", "31", "32", "33", "34", "35", "36", "37", "38", "39",
    "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
    "50", "51", "52", "53", "54", "55", "56", "57", "58", "59",
    "60", "61", "62", "63", "64", "65", "66", "67",
}

SHORT_NUMERIC_FIELD_BOUNDS = {
    "nbre_articles": (1, 99),
    "nombre_articles": (1, 99),
    "nombre_colis": (1, 999),
}

DEFAULT_RESULT_KEYS = [
    "exportateur", "adresse_exportateur", "code_exportateur",
    "importateur", "adresse_importateur", "code_importateur",
    "declarant", "repertoire", "numero_credit",
    "numero_declaration", "date_declaration", "numero_dae",
    "type_declaration", "nbre_articles", "nombre_articles", "nombre_colis",
    "exportateur_nom", "exportateur_code", "importateur_nom", "importateur_pays",
    "declarant_code", "declarant_nom",
    "transport_international_nationalite", "transport_international_mode",
    "transport_international_identite", "transport_national_nationalite",
    "transport_national_mode", "mode_transport", "date_arrivee_depart",
    "pays_provenance", "pays_achat", "pays_premiere_destination",
    "pays_destination", "pays_destination_finale", "adresse_entreposage",
    "mode_livraison", "mode_paiement", "relation_acheteur_vendeur",
    "engagement", "devise", "valeur_totale", "assurance", "fret",
    "montant_ptfn", "valeur_dinars", "valeur_fob_dt", "taux_conversion",
    "designation_marchandises", "numero_article", "code_sh_ndp",
    "code_pays_origine", "valeur_prise_en_charge", "code_qcs", "qcs",
    "pfn", "poids_brut", "poids_net", "qualite_fiscale",
    "regime_douanier", "imposition_speciale", "code_titre_ce", "numero_titre_ce",
    "code_regime_precedent", "code_regime_financier", "code_delai",
    "code_oci", "regime", "douane", "valeur_fob", "coefficient_ajustement",
    "description_marchandise", "bureau_frontiere", "destination",
    "localisation_export", "taxes", "articles", "bureau_douane",
    "code_bureau", "designation_bureau", "code_taxe", "assiette",
    "quotite", "montant", "code_gdt", "montant_total", "total",
    "totaux", "montant_liquidation", "itineraire", "commissaire_douane",
    "num_agrement", "num_repertoire", "texte_engagement", "nom_declarant",
    "date_validation", "cachet", "cle_authentification", "qr_code",
    "score_confiance", "qualite", "flags_validation",
]
