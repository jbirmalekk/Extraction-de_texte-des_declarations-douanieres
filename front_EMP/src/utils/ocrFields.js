export const DEFAULT_DOCUMENT_ID = 'INV-2024-0542';

const OCR_MODEL_FIELD_DEFS = [
	{ key: 'numero_declaration', label: 'Numero de Declaration', section: 'Identification', required: true, confidence: 95, demo: 'FR-2024-DCL-054231' },
	{ key: 'date_declaration', label: 'Date de Declaration', section: 'Identification', required: true, confidence: 72, demo: '2024-01-15' },
	{ key: 'type_declaration', label: 'Type de Declaration', section: 'Identification', required: true, confidence: 88, demo: 'DAE' },
	{ key: 'nbre_articles', label: 'Nombre de Colis / Articles', section: 'Identification', confidence: 93, demo: '14' },

	{ key: 'exportateur_nom', label: 'Exportateur - Nom', section: 'Exportateur', required: true, confidence: 90, demo: 'ENGINEERING MACHINING IN PRECISION' },
	{ key: 'exportateur_code', label: 'Exportateur - Code', section: 'Exportateur', confidence: 84, demo: '1113819W' },

	{ key: 'importateur_nom', label: 'Importateur - Nom', section: 'Importateur', required: true, confidence: 89, demo: 'CL101 RHINETAL CTS' },
	{ key: 'importateur_pays', label: 'Importateur - Pays', section: 'Importateur', confidence: 91, demo: 'U.S.A' },

	{ key: 'declarant_code', label: 'Declarant - Code', section: 'Declarant', confidence: 86, demo: '5051' },
	{ key: 'declarant_nom', label: 'Declarant - Nom', section: 'Declarant', confidence: 88, demo: 'STE SMART CUSTOMS BROKERS TUNIS' },

	{ key: 'mode_transport', label: 'Mode de Transport', section: 'Transport', confidence: 82, demo: 'VOL DU' },
	{ key: 'date_arrivee_depart', label: 'Date Arrivee / Depart', section: 'Transport', confidence: 80, demo: '24-12-2025' },
	{ key: 'pays_provenance', label: 'Pays de Provenance', section: 'Transport', confidence: 91, demo: 'TUNISIE' },
	{ key: 'pays_destination', label: 'Pays de Destination', section: 'Transport', confidence: 89, demo: 'PAYS BAS' },
	{ key: 'adresse_entreposage', label: 'Adresse Entreposage', section: 'Transport', confidence: 77, demo: 'SUITE SE 600204 DU 30-06-2025' },

	{ key: 'mode_livraison', label: 'Mode de Livraison', section: 'Finances', confidence: 78, demo: 'EXW' },
	{ key: 'devise', label: 'Devise', section: 'Finances', confidence: 92, demo: 'USD' },
	{ key: 'montant_ptfn', label: 'Montant PTFN', section: 'Finances', confidence: 58, demo: '10500.000', forceError: true },
	{ key: 'valeur_fob_dt', label: 'Valeur FOB (DT)', section: 'Finances', confidence: 75, demo: '30542.400' },
	{ key: 'taux_conversion', label: 'Taux Conversion', section: 'Finances', confidence: 76, demo: '2.908800' },

	{ key: 'designation_marchandises', label: 'Designation Marchandises', section: 'Marchandises', confidence: 85, demo: "Autres parties d'avions" },
	{ key: 'poids_brut', label: 'Poids Brut (kg)', section: 'Marchandises', confidence: 83, demo: '139' },
	{ key: 'poids_net', label: 'Poids Net (kg)', section: 'Marchandises', confidence: 77, demo: '61' },

	{ key: 'taxes', label: 'Taxes (JSON)', section: 'Listes', isJson: true, demo: '[{"code":"602","assiette":"13.000","quotite":"0.000000","montant":"0.000"}]' },
	{ key: 'articles', label: 'Articles (JSON)', section: 'Listes', isJson: true, demo: '[{"num_ligne":1,"code_hs":"88073000011","designation":"Autres parties d\'avions"}]' },

	{ key: 'bureau_douane', label: 'Bureau de Douane', section: 'Liquidation', required: true, confidence: 90, demo: 'BR - ARIANA' },
	{ key: 'code_gdt', label: 'Code GDT', section: 'Liquidation', confidence: 82, demo: '9' },
	{ key: 'montant_liquidation', label: 'Montant Liquidation', section: 'Liquidation', confidence: 81, demo: '13.000' },
	{ key: 'itineraire', label: 'Itineraire', section: 'Liquidation', confidence: 87, demo: 'SFAX-TC' },
	{ key: 'num_agrement', label: 'Numero Agrement', section: 'Liquidation', confidence: 88, demo: '935' },
	{ key: 'num_repertoire', label: 'Numero Repertoire', section: 'Liquidation', confidence: 84, demo: '2858' },
	{ key: 'cle_authentification', label: 'Cle Authentification', section: 'Liquidation', required: true, confidence: 86, demo: 'D5051DDMW' },

	{ key: 'score_confiance', label: 'Score Confiance', section: 'Qualite OCR', confidence: 96, demo: '82' },
	{ key: 'qualite', label: 'Qualite OCR', section: 'Qualite OCR', confidence: 96, demo: 'HAUT' },
	{ key: 'flags_validation', label: 'Flags Validation (JSON)', section: 'Qualite OCR', isJson: true, demo: '[]' },

	{ key: 'fichier', label: 'Fichier Source', section: 'Metadonnees', confidence: null, demo: 'document.jpg' },
	{ key: 'nb_cellules', label: 'Nombre de Cellules', section: 'Metadonnees', confidence: null, demo: '12' },
];

const VALIDATION_ALLOWED_KEYS = new Set([
	'numero_declaration',
	'date_declaration',
	'type_declaration',
	'exportateur_nom',
	'importateur_nom',
	'importateur_pays',
	'mode_transport',
	'devise',
	'montant_ptfn',
	'valeur_fob_dt',
	'bureau_douane',
	'montant_liquidation',
]);

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
	} catch (_error) {
		return String(value);
	}
};

const mapOneField = (def, result) => {
	const rawValue = result?.[def.key];
	const fromBackend = def.isJson ? toJsonString(rawValue) : toScalarString(rawValue);
	const fallback = def.demo || '';
	const value = fromBackend.length > 0 ? fromBackend : fallback;
	const isMissing = value.trim().length === 0;
	const hasError = def.required ? isMissing : Boolean(def.forceError && fromBackend.length === 0);

	return {
		id: def.key,
		key: def.key,
		label: def.label,
		section: def.section,
		value,
		confidence: typeof def.confidence === 'number' ? def.confidence : null,
		hasError,
		isManual: false,
	};
};

export const mapBackendResultToFields = (result = {}) => OCR_MODEL_FIELD_DEFS.map((def) => mapOneField(def, result));

export const DEFAULT_EXTRACTED_FIELDS = mapBackendResultToFields({});

export const buildBackendValidationPayload = (fields, documentId, statut = 'valide') => {
	const payload = {
		document_id: Number(documentId),
		statut,
	};

	fields.forEach((field) => {
		const key = field.key || field.id;
		if (!key || field.isManual || !VALIDATION_ALLOWED_KEYS.has(key)) {
			return;
		}

		const value = toScalarString(field.value);
		if (value.length > 0) {
			payload[key] = value;
		}
	});

	return payload;
};
