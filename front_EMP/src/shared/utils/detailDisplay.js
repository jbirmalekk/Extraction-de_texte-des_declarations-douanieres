import { mapBackendResultToFields } from '@/shared/utils/ocrFields';
import { mapInvoiceBackendToFields } from '@/shared/utils/invoiceFields';

const hasValue = (value) => value != null && String(value).trim() !== '';

/** Sections masquées sur la page détail DUM (doublons JSON / métriques déjà dans le résumé ou onglet Articles & taxes). */
export const DUM_DETAIL_EXCLUDED_SECTIONS = new Set(['Listes', 'Qualite OCR']);

/** Ordre d'affichage des sections DUM (page détail). */
export const DUM_SECTION_ORDER = [
	'Identification',
	'Informations generales',
	'Declarant',
	'Transport',
	'Finances',
	'Logistique',
	'Marchandises',
	'Liquidation',
	'Metadonnees',
];

export const INVOICE_SECTION_ORDER = [
	'Identification',
	'Client',
	'Montants',
	'Logistique',
	'Conditions',
	'Controle DUM',
	'Lignes facture',
	'Metadonnees',
];

const groupFieldsBySection = (fields, sectionOrder) => {
	const groups = new Map();
	for (const field of fields) {
		const section = field.section || 'Autres';
		if (!groups.has(section)) {
			groups.set(section, []);
		}
		groups.get(section).push(field);
	}
	const ordered = [];
	for (const name of sectionOrder) {
		if (groups.has(name)) {
			ordered.push({ section: name, fields: groups.get(name) });
			groups.delete(name);
		}
	}
	for (const [section, sectionFields] of groups.entries()) {
		ordered.push({ section, fields: sectionFields });
	}
	return ordered;
};

/**
 * Tous les champs DUM extraits (définitions OCR_MODEL_FIELD_DEFS).
 * @param {object} document — réponse API document
 * @param {{ showEmpty?: boolean }} [opts]
 */
export const buildDumDetailSections = (document, { showEmpty = false } = {}) => {
	if (!document) {
		return [];
	}
	const fields = mapBackendResultToFields(document, { useDemoFallback: false }).filter(
		(def) => !def.hidden && !DUM_DETAIL_EXCLUDED_SECTIONS.has(def.section)
	);
	const visible = showEmpty ? fields : fields.filter((f) => hasValue(f.value));
	return groupFieldsBySection(visible, DUM_SECTION_ORDER);
};

/**
 * Tous les champs facture (scalaires + contrôle DUM + lignes aplaties).
 */
export const buildInvoiceDetailSections = (invoice, { showEmpty = false } = {}) => {
	if (!invoice) {
		return [];
	}
	const fields = mapInvoiceBackendToFields(invoice, {
		onlyPopulated: !showEmpty,
		includeControleDum: true,
	});
	const scalarFields = fields.filter((f) => f.section !== 'Lignes facture');
	const lineFields = fields.filter((f) => f.section === 'Lignes facture');
	const sections = groupFieldsBySection(scalarFields, INVOICE_SECTION_ORDER);
	if (lineFields.length > 0) {
		sections.push({ section: 'Lignes facture (détail)', fields: lineFields });
	}
	return sections;
};

export const formatDumStatut = (statut) => {
	const s = String(statut || '').toLowerCase();
	if (s === 'validated' || s === 'valide') {
		return { label: 'Validé', tone: 'success' };
	}
	if (s === 'rejected' || s === 'rejete') {
		return { label: 'Rejeté', tone: 'error' };
	}
	if (s === 'processing' || s === 'en_cours') {
		return { label: 'En cours', tone: 'warning' };
	}
	if (s === 'done' || s === 'termine') {
		return { label: 'Traité', tone: 'success' };
	}
	return { label: statut || 'En attente', tone: 'warning' };
};

export const formatInvoiceStatut = (statut) => {
	const s = String(statut || '').toLowerCase();
	if (s === 'valide') {
		return { label: 'Validée', tone: 'success' };
	}
	if (s === 'controle_croise') {
		return { label: 'Contrôle croisé', tone: 'success' };
	}
	if (s === 'extracted') {
		return { label: 'Extraite', tone: 'warning' };
	}
	return { label: statut || '—', tone: 'warning' };
};

export const formatControleTone = (statutControle) => {
	if (statutControle === 'ok') {
		return { label: 'Conforme', tone: 'ok' };
	}
	if (statutControle === 'warning') {
		return { label: 'Attention', tone: 'warning' };
	}
	if (statutControle === 'error') {
		return { label: 'Écart', tone: 'error' };
	}
	return { label: '—', tone: 'neutral' };
};

export const countPopulatedFields = (sections) =>
	sections.reduce((n, s) => n + s.fields.filter((f) => hasValue(f.value)).length, 0);
