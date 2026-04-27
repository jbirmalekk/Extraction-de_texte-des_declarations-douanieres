/*
Migration SQL Server - Ajout des champs étendus déclaration dans documents
Objectif: permettre les requêtes SQL directes sur les champs les plus demandés
*/

SET NOCOUNT ON;

IF COL_LENGTH('documents', 'adresse_exportateur') IS NULL
    ALTER TABLE documents ADD adresse_exportateur NVARCHAR(MAX) NULL;

IF COL_LENGTH('documents', 'adresse_importateur') IS NULL
    ALTER TABLE documents ADD adresse_importateur NVARCHAR(MAX) NULL;

IF COL_LENGTH('documents', 'code_importateur') IS NULL
    ALTER TABLE documents ADD code_importateur NVARCHAR(50) NULL;

IF COL_LENGTH('documents', 'numero_dae') IS NULL
    ALTER TABLE documents ADD numero_dae NVARCHAR(50) NULL;

IF COL_LENGTH('documents', 'nombre_articles') IS NULL
    ALTER TABLE documents ADD nombre_articles NVARCHAR(20) NULL;

IF COL_LENGTH('documents', 'nombre_colis') IS NULL
    ALTER TABLE documents ADD nombre_colis NVARCHAR(20) NULL;

IF COL_LENGTH('documents', 'numero_credit') IS NULL
    ALTER TABLE documents ADD numero_credit NVARCHAR(50) NULL;

IF COL_LENGTH('documents', 'pays_achat') IS NULL
    ALTER TABLE documents ADD pays_achat NVARCHAR(100) NULL;

IF COL_LENGTH('documents', 'pays_premiere_destination') IS NULL
    ALTER TABLE documents ADD pays_premiere_destination NVARCHAR(100) NULL;

IF COL_LENGTH('documents', 'pays_destination_finale') IS NULL
    ALTER TABLE documents ADD pays_destination_finale NVARCHAR(100) NULL;

IF COL_LENGTH('documents', 'transport_international_nationalite') IS NULL
    ALTER TABLE documents ADD transport_international_nationalite NVARCHAR(100) NULL;

IF COL_LENGTH('documents', 'transport_international_mode') IS NULL
    ALTER TABLE documents ADD transport_international_mode NVARCHAR(100) NULL;

IF COL_LENGTH('documents', 'transport_international_identite') IS NULL
    ALTER TABLE documents ADD transport_international_identite NVARCHAR(100) NULL;

IF COL_LENGTH('documents', 'transport_national_nationalite') IS NULL
    ALTER TABLE documents ADD transport_national_nationalite NVARCHAR(100) NULL;

IF COL_LENGTH('documents', 'transport_national_mode') IS NULL
    ALTER TABLE documents ADD transport_national_mode NVARCHAR(100) NULL;

IF COL_LENGTH('documents', 'mode_paiement') IS NULL
    ALTER TABLE documents ADD mode_paiement NVARCHAR(50) NULL;

IF COL_LENGTH('documents', 'relation_acheteur_vendeur') IS NULL
    ALTER TABLE documents ADD relation_acheteur_vendeur NVARCHAR(100) NULL;

IF COL_LENGTH('documents', 'engagement') IS NULL
    ALTER TABLE documents ADD engagement NVARCHAR(MAX) NULL;

IF COL_LENGTH('documents', 'valeur_totale') IS NULL
    ALTER TABLE documents ADD valeur_totale NVARCHAR(50) NULL;

IF COL_LENGTH('documents', 'assurance') IS NULL
    ALTER TABLE documents ADD assurance NVARCHAR(50) NULL;

IF COL_LENGTH('documents', 'fret') IS NULL
    ALTER TABLE documents ADD fret NVARCHAR(50) NULL;

IF COL_LENGTH('documents', 'valeur_dinars') IS NULL
    ALTER TABLE documents ADD valeur_dinars NVARCHAR(50) NULL;

IF COL_LENGTH('documents', 'code_bureau') IS NULL
    ALTER TABLE documents ADD code_bureau NVARCHAR(50) NULL;

IF COL_LENGTH('documents', 'designation_bureau') IS NULL
    ALTER TABLE documents ADD designation_bureau NVARCHAR(150) NULL;

IF COL_LENGTH('documents', 'bureau_frontiere') IS NULL
    ALTER TABLE documents ADD bureau_frontiere NVARCHAR(150) NULL;

IF COL_LENGTH('documents', 'destination') IS NULL
    ALTER TABLE documents ADD destination NVARCHAR(150) NULL;

IF COL_LENGTH('documents', 'localisation_export') IS NULL
    ALTER TABLE documents ADD localisation_export NVARCHAR(150) NULL;

IF COL_LENGTH('documents', 'montant_total') IS NULL
    ALTER TABLE documents ADD montant_total NVARCHAR(50) NULL;

IF COL_LENGTH('documents', 'total') IS NULL
    ALTER TABLE documents ADD total NVARCHAR(50) NULL;

IF COL_LENGTH('documents', 'totaux') IS NULL
    ALTER TABLE documents ADD totaux NVARCHAR(50) NULL;

IF COL_LENGTH('documents', 'commissaire_douane') IS NULL
    ALTER TABLE documents ADD commissaire_douane NVARCHAR(200) NULL;

IF COL_LENGTH('documents', 'texte_engagement') IS NULL
    ALTER TABLE documents ADD texte_engagement NVARCHAR(MAX) NULL;

IF COL_LENGTH('documents', 'nom_declarant') IS NULL
    ALTER TABLE documents ADD nom_declarant NVARCHAR(200) NULL;

IF COL_LENGTH('documents', 'date_validation') IS NULL
    ALTER TABLE documents ADD date_validation NVARCHAR(50) NULL;

IF COL_LENGTH('documents', 'cachet') IS NULL
    ALTER TABLE documents ADD cachet NVARCHAR(200) NULL;

IF COL_LENGTH('documents', 'qr_code') IS NULL
    ALTER TABLE documents ADD qr_code NVARCHAR(500) NULL;
