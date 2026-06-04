export const DEFAULT_DOCUMENT_ID = 'INV-2024-0542';

const OCR_MODEL_FIELD_DEFS = [
	// 1. Informations generales
	{ key: 'exportateur', label: 'Exportateur', section: 'Informations generales' },
	{ key: 'adresse_exportateur', label: 'Adresse exportateur', section: 'Informations generales' },
	{ key: 'code_exportateur', label: 'Code exportateur', section: 'Informations generales' },
	{ key: 'importateur', label: 'Importateur', section: 'Informations generales' },
	{ key: 'importateur_pays', label: 'Importateur - Pays', section: 'Informations generales', confidence: 91, demo: 'U.S.A' },
	{ key: 'code_importateur', label: 'Code importateur', section: 'Informations generales' },
	{ key: 'declarant', label: 'Declarant', section: 'Informations generales' },
	{ key: 'repertoire', label: 'Repertoire', section: 'Informations generales' },
	{ key: 'numero_credit', label: 'Numero credit', section: 'Informations generales' },
	// 2. Declaration
	{ key: 'numero_declaration', label: 'Numero de Declaration', section: 'Identification', required: true, confidence: 95, demo: 'FR-2024-DCL-054231' },
	{ key: 'date_declaration', label: 'Date de Declaration', section: 'Identification', required: true, confidence: 72, demo: '2024-01-15' },
	{ key: 'numero_dae', label: 'Numero D.A.E', section: 'Identification' },
	{ key: 'type_declaration', label: 'Type de Declaration', section: 'Identification', required: true, confidence: 88, demo: 'DAE' },
	{ key: 'nombre_articles', label: 'Nombre total d articles', section: 'Identification' },
	{ key: 'nombre_colis', label: 'Nombre total de colis', section: 'Identification' },


	{ key: 'declarant_code', label: 'Declarant - Code', section: 'Declarant', confidence: 86, demo: '5051', hidden: true },
	{ key: 'declarant_nom', label: 'Declarant - Nom', section: 'Declarant', confidence: 88, demo: 'STE SMART CUSTOMS BROKERS TUNIS', hidden: true },

	{ key: 'mode_transport', label: 'Mode de Transport', section: 'Transport', confidence: 82, demo: 'VOL DU' },
	{ key: 'date_arrivee_depart', label: 'Date Arrivee / Depart', section: 'Transport', confidence: 80, demo: '24-12-2025' },
	{ key: 'transport_international_nationalite', label: 'Transport international - Nationalite', section: 'Transport' },
	{ key: 'transport_international_mode', label: 'Transport international - Mode', section: 'Transport' },
	{ key: 'transport_international_identite', label: 'Transport international - Identite', section: 'Transport' },
	{ key: 'transport_national_nationalite', label: 'Transport national - Nationalite', section: 'Transport' },
	{ key: 'transport_national_mode', label: 'Transport national - Mode', section: 'Transport' },
	{ key: 'pays_provenance', label: 'Pays de Provenance', section: 'Transport', confidence: 91, demo: 'TUNISIE' },
	{ key: 'pays_achat', label: 'Pays d achat', section: 'Transport' },
	{ key: 'pays_premiere_destination', label: 'Pays premiere destination', section: 'Transport' },
	{ key: 'pays_destination_finale', label: 'Pays destination definitive', section: 'Transport' },
	{ key: 'adresse_entreposage', label: 'Adresse Entreposage', section: 'Transport', confidence: 77, demo: 'SUITE SE 600204 DU 30-06-2025' },

	// 5. Financier
	{ key: 'mode_livraison', label: 'Mode de Livraison', section: 'Finances', confidence: 78, demo: 'EXW' },
	{ key: 'mode_paiement', label: 'Mode de paiement', section: 'Finances' },
	{ key: 'relation_acheteur_vendeur', label: 'Relation acheteur/vendeur', section: 'Finances' },
	{ key: 'engagement', label: 'Engagement', section: 'Finances' },
	{ key: 'engag_c', label: 'Engag C', section: 'Finances' },
	{ key: 'devise', label: 'Devise', section: 'Finances', confidence: 92, demo: 'USD' },
	{ key: 'montant_ptfn', label: 'Montant PTFN', section: 'Finances', confidence: 58, demo: '10500.000', forceError: true },
	{ key: 'solde_autres_elements_ptfn', label: 'Solde autres elements PTFN', section: 'Finances' },
	{ key: 'fret', label: 'Fret', section: 'Finances' },
	{ key: 'assurance', label: 'Assurance', section: 'Finances' },
	
	{ key: 'taux_conversion', label: 'Cours de Conversion de la devise de facturation', section: 'Finances', confidence: 76, demo: '2.908800' },
	//{ key: 'valeur_fob_dt', label: 'Valeur FOB (DT)', section: 'Finances', confidence: 75, demo: '30542.400' },
	{ key: 'valeur_dinars', label: 'Valeur douane totale en dinars', section: 'Finances' },

	// 6. Logistique
	{ key: 'bureau_frontiere', label: 'Bureau frontiere', section: 'Logistique' },
	{ key: 'destination', label: 'Destination', section: 'Logistique' },
	{ key: 'localisation_export', label: 'Localisation ', section: 'Logistique' },

	{ key: 'designation_marchandises', label: 'Designation Marchandises', section: 'Marchandises', confidence: 85, demo: "Autres parties d'avions" },
	{ key: 'numero_article', label: 'Numero article', section: 'Marchandises' },
	{ key: 'code_sh_ndp', label: 'Code SH (NDP)', section: 'Marchandises' },
	{ key: 'code_pays_origine', label: 'Code pays origine', section: 'Marchandises' },
	{ key: 'valeur_prise_en_charge', label: 'Valeur prise en charge sous rég-précedent', section: 'Marchandises' },
	{ key: 'code_qcs', label: 'Code QCS', section: 'Marchandises' },
	{ key: 'qcs', label: 'QCS', section: 'Marchandises' },
	{ key: 'pfn', label: "PFN de l'article", section: 'Marchandises' },
	{ key: 'poids_brut', label: 'Poids Brut (kg)', section: 'Marchandises', confidence: 83, demo: '139' },
	{ key: 'poids_net', label: 'Poids Net (kg)', section: 'Marchandises', confidence: 77, demo: '61' },
	{ key: 'qualite_fiscale', label: 'Qualite fiscale', section: 'Marchandises' },
	{ key: 'imposition_speciale', label: 'Regime douanier declare', section: 'Marchandises' },
	{ key: 'code_regime_transit', label: 'Regime douanier transit', section: 'Marchandises' },
	{ key: 'code_regime_precedent', label: 'Regime douanier precedent', section: 'Marchandises' },
	{ key: 'code_regime_financier', label: 'Code reglement financier', section: 'Marchandises' },
	{ key: 'code_delai', label: 'Code delai', section: 'Marchandises' },
	{ key: 'code_oci', label: 'Code QCI', section: 'Marchandises' },
	{ key: 'regime', label: 'Regime', section: 'Marchandises' },
	{ key: 'code_titre_ce', label: 'Code Titre CE', section: 'Marchandises' },
	{ key: 'numero_titre_ce', label: 'Numero Titre CE', section: 'Marchandises' },
	{ key: 'valeur_fob', label: 'FOB (valeur en dinars)', section: 'Marchandises' },
	{ key: 'douane', label: 'Douane (valeur en dinars)', section: 'Marchandises' },
	{ key: 'coefficient_ajustement', label: 'Coefficient ajustement', section: 'Marchandises' },

	// 9. Taxes/Liquidation
	{ key: 'code_taxe', label: 'Code taxe', section: 'Liquidation' },
	{ key: 'assiette', label: 'Assiette', section: 'Liquidation' },
	{ key: 'quotite', label: 'Quotite', section: 'Liquidation' },
	{ key: 'montant', label: 'Montant', section: 'Liquidation' },
	{ key: 'taxes', label: 'Taxes (JSON)', section: 'Listes', isJson: true, demo: '[{"code":"602","assiette":"13.000","quotite":"0.000000","montant":"0.000"}]' },
	{ key: 'articles', label: 'Articles (JSON)', section: 'Listes', isJson: true, demo: '[{"num_ligne":1,"code_hs":"88073000011","designation":"Autres parties d\'avions"}]' },

	{ key: 'bureau_douane', label: 'Bureau de Douane', section: 'Liquidation', required: true, confidence: 90, demo: 'BR - ARIANA' },
	{ key: 'code_bureau', label: 'Code bureau', section: 'Liquidation' },
	{ key: 'designation_bureau', label: 'Designation bureau', section: 'Liquidation' },
	{ key: 'code_gdt', label: 'Code GDT', section: 'Liquidation', confidence: 82, demo: '9' },
	{ key: 'montant_liquidation', label: 'Montant Liquidation', section: 'Liquidation', confidence: 81, demo: '13.000' },
	{ key: 'montant_total', label: 'Montant total', section: 'Liquidation' },
	{ key: 'total', label: 'Total', section: 'Liquidation' },
	{ key: 'totaux', label: 'Totaux', section: 'Liquidation' },
	{ key: 'certificat_decharge', label: 'Certificat de decharge', section: 'Liquidation' },
	{ key: 'numero_escale', label: 'Numero escale', section: 'Liquidation' },
	{ key: 'rubrique', label: 'Rubrique', section: 'Liquidation' },
	{ key: 'itineraire', label: 'Itineraire', section: 'Liquidation', confidence: 87, demo: 'SFAX-TC' },
	{ key: 'commissaire_douane', label: 'Commissaire en douane', section: 'Liquidation' },
	{ key: 'num_agrement', label: 'Numero Agrement', section: 'Liquidation', confidence: 88, demo: '935' },
	{ key: 'num_repertoire', label: 'Numero Repertoire', section: 'Liquidation', confidence: 84, demo: '2858' },
	{ key: 'texte_engagement', label: 'Texte engagement', section: 'Liquidation' },
	{ key: 'nom_declarant', label: 'Nom declarant', section: 'Liquidation' },
	{ key: 'date_validation', label: 'Date validation', section: 'Liquidation' },
	{ key: 'cachet', label: 'Cachet', section: 'Liquidation' },
	{ key: 'cle_authentification', label: 'Cle Authentification', section: 'Liquidation', required: true, confidence: 86, demo: 'D5051DDMW' },


	{ key: 'score_confiance', label: 'Score Confiance', section: 'Qualite OCR', confidence: 96, demo: '82' },
	{ key: 'qualite', label: 'Qualite OCR', section: 'Qualite OCR', confidence: 96, demo: 'HAUT' },
	{ key: 'flags_validation', label: 'Flags Validation (JSON)', section: 'Qualite OCR', isJson: true, demo: '[]' },

	{ key: 'fichier', label: 'Fichier Source', section: 'Metadonnees', confidence: null, demo: 'document.jpg' },
	{ key: 'nb_cellules', label: 'Nombre de Cellules', section: 'Metadonnees', confidence: null, demo: '12' },
];

const FIELD_VALUE_ALIASES = {
	exportateur: ['exportateur_nom'],
	code_exportateur: ['exportateur_code'],
	importateur: ['importateur_nom'],
	code_importateur: ['importateur_code'],
	declarant: ['declarant_nom'],
	repertoire: ['num_repertoire'],
	nombre_articles: ['nbre_articles'],
	pays_destination_finale: ['pays_destination'],
	transport_international_mode: ['mode_transport'],
	valeur_dinars: ['valeur_fob_dt', 'douane'],
	valeur_fob: ['valeur_fob_dt'],
	designation_marchandise: ['designation_marchandises'],
	designation_bureau: ['bureau_douane'],
	nom_declarant: ['declarant_nom'],
};

const NON_EDITABLE_SECTIONS = new Set(['Listes', 'Qualite OCR', 'Metadonnees']);

const VALIDATION_ALLOWED_KEYS = new Set(
	OCR_MODEL_FIELD_DEFS
		.filter((def) => !def.isJson && !NON_EDITABLE_SECTIONS.has(def.section))
		.map((def) => def.key)
);

const toScalarString = (value) => {
	if (value === null || value === undefined) {
		return '';
	}
	const serialized = String(value).trim();
	return serialized;
};

const toJsonString = (value) => {
	if (value === null || value === undefined) {
		return '';
	}
	if (typeof value === 'string') {
		return value;
	}
	try {
		return JSON.stringify(value);
	} catch {
		return String(value);
	}
};

const toConfidenceNumber = (value) => {
	if (value === null || value === undefined || value === '') {
		return null;
	}
	const numericValue = Number(value);
	return Number.isFinite(numericValue) ? numericValue : null;
};

const resolveBackendConfidence = (result, key) => {
	if (!result || !key) {
		return null;
	}

	const containers = [
		result.field_confidences,
		result.field_confidence,
		result.confidences,
		result.confidence_by_field,
		result.scores_by_field,
	];

	for (const container of containers) {
		if (!container || typeof container !== 'object') {
			continue;
		}
		const directValue = container[key] ?? container[`tpl_${key}`];
		if (directValue && typeof directValue === 'object') {
			const nestedConfidence = toConfidenceNumber(directValue.confidence ?? directValue.score);
			if (nestedConfidence !== null) {
				return nestedConfidence;
			}
		}
		const confidence = toConfidenceNumber(directValue);
		if (confidence !== null) {
			return confidence;
		}
	}

	const fieldValue = result.fields?.[key] ?? result.ocr_fields?.[key];
	if (fieldValue && typeof fieldValue === 'object') {
		return toConfidenceNumber(fieldValue.confidence ?? fieldValue.score);
	}

	return null;
};

const mapOneField = (def, result, options = {}) => {
	const { useDemoFallback = false } = options;
	const candidateKeys = [def.key, ...(FIELD_VALUE_ALIASES[def.key] || [])];
	const resolvedKey = candidateKeys.find((key) => result?.[key] !== undefined && result?.[key] !== null);
	const rawValue = resolvedKey ? result?.[resolvedKey] : result?.[def.key];
	const fromBackend = def.isJson ? toJsonString(rawValue) : toScalarString(rawValue);
	const fallback = useDemoFallback ? def.demo || '' : '';
	const value = fromBackend.length > 0 ? fromBackend : fallback;
	const isMissing = value.trim().length === 0;
	const hasError = def.required ? isMissing : Boolean(def.forceError && fromBackend.length === 0);

	return {
		id: def.key,
		key: def.key,
		label: def.label,
		section: def.section,
		value,
		confidence: resolveBackendConfidence(result, resolvedKey || def.key) ?? resolveBackendConfidence(result, def.key),
		hasError,
		isManual: false,
	};
};

export const mapBackendResultToFields = (result = {}, options = {}) =>
	OCR_MODEL_FIELD_DEFS
		.filter((def) => !def.hidden)
		.map((def) => mapOneField(def, result, options));

export const MISSING_FIELD_OPTIONS = OCR_MODEL_FIELD_DEFS
	.filter((def) => !def.hidden && !def.isJson && !NON_EDITABLE_SECTIONS.has(def.section))
	.map((def) => ({ key: def.key, label: def.label, section: def.section }));

export const DEFAULT_EXTRACTED_FIELDS = mapBackendResultToFields({}, { useDemoFallback: true });

export const buildBackendValidationPayload = (fields, documentId, statut = 'valide') => {
	const payload = {
		document_id: Number(documentId),
		statut,
	};

	fields.forEach((field) => {
		const key = field.key || field.id;
		if (!key || !VALIDATION_ALLOWED_KEYS.has(key)) {
			return;
		}

		const value = toScalarString(field.value);
		payload[key] = value;
	});

	return payload;
};
