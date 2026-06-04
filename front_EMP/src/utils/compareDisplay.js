const DEFAULT_AMOUNT_TOLERANCE = 0.01;

const formatMoney = (value, devise = '') => {
	if (value == null || value === '') {
		return '—';
	}
	const n = Number(value);
	const formatted = Number.isFinite(n)
		? n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
		: String(value);
	return devise ? `${formatted} ${devise}`.trim() : formatted;
};

const parseAmount = (val) => {
	if (val == null || val === '') {
		return null;
	}
	const n = Number(String(val).replace(/\s/g, '').replace(',', '.'));
	return Number.isFinite(n) ? n : null;
};

const severityToStatus = (severity) => {
	if (severity === 'error') {
		return { label: 'Écart', tone: 'error' };
	}
	if (severity === 'warning') {
		return { label: 'Attention', tone: 'warning' };
	}
	return { label: 'Conforme', tone: 'ok' };
};

const formatScalar = (val, suffix = '') => {
	if (val == null || val === '') {
		return '—';
	}
	const s = String(val).trim();
	return suffix ? `${s} ${suffix}`.trim() : s;
};

const valuesEqual = (a, b) => {
	if (a == null || a === '' || b == null || b === '') {
		return null;
	}
	const na = parseAmount(a);
	const nb = parseAmount(b);
	if (na != null && nb != null) {
		return Math.abs(na - nb) < 0.01;
	}
	return String(a).trim().toUpperCase() === String(b).trim().toUpperCase();
};

/** Ordre fixe des lignes — identique que la comparaison parte de la DUM ou de la facture. */
const FIXED_ROW_ORDER = [
	'montant_net_pay_vs_pfn',
	'currency_mismatch',
	'colis_mismatch',
	'poids_net_mismatch',
	'incoterm_mismatch',
	'numero_declaration',
];

const resolvePfnAmount = (invoiceResult, dumMeta = {}) =>
	parseAmount(invoiceResult?.montant_declare_dum) ??
	parseAmount(invoiceResult?.montant_pfn_dum) ??
	parseAmount(dumMeta?.montant_ptfn);

const resolveNetPayAmount = (invoiceResult, invoiceMeta = {}) =>
	parseAmount(invoiceResult?.net_pay) ??
	parseAmount(invoiceMeta?.net_pay) ??
	parseAmount(invoiceResult?.montant_ttc) ??
	parseAmount(invoiceMeta?.montant_ttc);

/**
 * Totaux PFN / NET PAY alignés — recalcul côté UI pour éviter un faux « conforme »
 * (ex. ecart_montant à 0 alors que statut_controle = error).
 */
export const isMontantAligned = (
	invoiceResult,
	dumMeta = {},
	invoiceMeta = {},
	tolerance = DEFAULT_AMOUNT_TOLERANCE
) => {
	if (!invoiceResult) {
		return false;
	}
	if (invoiceResult.statut_controle === 'error') {
		return false;
	}
	const anomalies = Array.isArray(invoiceResult.controle_anomalies)
		? invoiceResult.controle_anomalies
		: [];
	if (
		anomalies.some(
			(a) =>
				a?.code === 'amount_gap' &&
				(a.severity === 'error' || a.severity === 'warning')
		)
	) {
		return false;
	}

	const pfn = resolvePfnAmount(invoiceResult, dumMeta);
	const netPay = resolveNetPayAmount(invoiceResult, invoiceMeta);
	if (pfn != null && netPay != null) {
		return Math.abs(netPay - pfn) <= tolerance;
	}

	const ecart = Number(invoiceResult.ecart_montant);
	if (!Number.isFinite(ecart)) {
		return invoiceResult.statut_controle === 'ok';
	}
	return Math.abs(ecart) <= tolerance;
};

/** Libellé de synthèse pour la bannière de conformité montants. */
export const getMontantAlignmentSummary = (invoiceResult, dumMeta = {}, invoiceMeta = {}) => {
	const aligned = isMontantAligned(invoiceResult, dumMeta, invoiceMeta);
	const pfn = resolvePfnAmount(invoiceResult, dumMeta);
	const netPay = resolveNetPayAmount(invoiceResult, invoiceMeta);
	const ecart =
		pfn != null && netPay != null
			? netPay - pfn
			: Number(invoiceResult?.ecart_montant);
	const devise =
		invoiceResult?.devise_declaree_dum ||
		dumMeta?.devise ||
		invoiceResult?.devise ||
		invoiceMeta?.devise ||
		'';
	return {
		aligned,
		pfn,
		netPay,
		ecartAbs: Number.isFinite(ecart) ? Math.abs(ecart) : null,
		devise,
		statutControle: invoiceResult?.statut_controle || null,
	};
};

/**
 * Tableau de réconciliation : mêmes catégories et colonnes dans tous les cas.
 * @param {object} invoiceResult — réponse compare / facture
 * @param {object} [dumMeta] — détail document DUM (API 8000)
 * @param {object} [invoiceMeta] — détail facture (API 8001)
 */
export const buildComparisonRows = (invoiceResult, dumMeta = {}, invoiceMeta = {}) => {
	const anomalyMap = {};
	for (const a of invoiceResult?.controle_anomalies || []) {
		if (a?.code) {
			anomalyMap[a.code] = a;
		}
	}

	const pfn = resolvePfnAmount(invoiceResult, dumMeta);
	const netPay = resolveNetPayAmount(invoiceResult, invoiceMeta);
	const devDum = (
		invoiceResult?.devise_declaree_dum ||
		dumMeta?.devise ||
		''
	)
		.toString()
		.trim();
	const devInv = (invoiceResult?.devise || invoiceMeta?.devise || '').toString().trim();
	const ecart = invoiceResult?.ecart_montant;
	const amountAligned = isMontantAligned(invoiceResult, dumMeta, invoiceMeta);

	const colisDum =
		anomalyMap.colis_mismatch?.dum_value ??
		dumMeta?.nombre_colis ??
		invoiceResult?.nombre_colis_dum;
	const colisInv = anomalyMap.colis_mismatch?.facture_value ?? invoiceMeta?.nombre_colis;

	const poidsDum =
		anomalyMap.poids_net_mismatch?.dum_value ??
		parseAmount(dumMeta?.poids_net) ??
		invoiceResult?.poids_net_kg_dum;
	const poidsInv =
		anomalyMap.poids_net_mismatch?.facture_value ??
		invoiceMeta?.poids_net_kg;

	const incotermDum =
		anomalyMap.incoterm_mismatch?.dum_value ??
		dumMeta?.mode_livraison ??
		dumMeta?.incoterm;
	const incotermInv =
		anomalyMap.incoterm_mismatch?.facture_value ?? invoiceMeta?.incoterm;

	const numDecl =
		invoiceResult?.numero_declaration_dum ||
		anomalyMap.declaration_linked?.dum_value ||
		dumMeta?.numero_declaration;

	const rowBuilders = {
		montant_net_pay_vs_pfn: () => ({
			code: 'montant_net_pay_vs_pfn',
			categorie: 'NET PAY vs PFN (DUM)',
			dumValue: formatMoney(pfn, devDum),
			factureValue: formatMoney(netPay, devInv),
			ecart: formatMoney(ecart != null ? Math.abs(Number(ecart)) : null, devDum || devInv),
			...(amountAligned
				? { statut: 'Conforme', tone: 'ok' }
				: anomalyMap.amount_gap?.severity === 'error'
					? { statut: 'Écart', tone: 'error' }
					: { statut: 'Attention', tone: 'warning' }),
		}),
		currency_mismatch: () => {
			const mismatch =
				Boolean(anomalyMap.currency_mismatch) ||
				(devDum && devInv && devDum.toUpperCase() !== devInv.toUpperCase());
			return {
				code: 'currency_mismatch',
				categorie: 'Devise',
				dumValue: formatScalar(devDum || anomalyMap.currency_mismatch?.dum_value),
				factureValue: formatScalar(devInv || anomalyMap.currency_mismatch?.facture_value),
				ecart: '—',
				...(mismatch
					? { statut: 'Attention', tone: 'warning' }
					: { statut: 'Conforme', tone: 'ok' }),
			};
		},
		colis_mismatch: () => {
			const eq = valuesEqual(colisDum, colisInv);
			const hasAnomaly = Boolean(anomalyMap.colis_mismatch);
			let statut = '—';
			let tone = 'neutral';
			if (hasAnomaly) {
				({ label: statut, tone } = severityToStatus('warning'));
			} else if (eq === true) {
				statut = 'Conforme';
				tone = 'ok';
			} else if (eq === false) {
				statut = 'Attention';
				tone = 'warning';
			}
			return {
				code: 'colis_mismatch',
				categorie: 'Nombre de colis',
				dumValue: formatScalar(colisDum),
				factureValue: formatScalar(colisInv),
				ecart: '—',
				statut,
				tone,
			};
		},
		poids_net_mismatch: () => {
			const eq = valuesEqual(poidsDum, poidsInv);
			const hasAnomaly = Boolean(anomalyMap.poids_net_mismatch);
			let statut = '—';
			let tone = 'neutral';
			if (hasAnomaly) {
				({ label: statut, tone } = severityToStatus('warning'));
			} else if (eq === true) {
				statut = 'Conforme';
				tone = 'ok';
			} else if (eq === false) {
				statut = 'Attention';
				tone = 'warning';
			}
			return {
				code: 'poids_net_mismatch',
				categorie: 'Poids net (kg)',
				dumValue: formatScalar(poidsDum, 'kg'),
				factureValue: formatScalar(poidsInv, 'kg'),
				ecart: '—',
				statut,
				tone,
			};
		},
		incoterm_mismatch: () => {
			const eq = valuesEqual(incotermDum, incotermInv);
			const hasAnomaly = Boolean(anomalyMap.incoterm_mismatch);
			let statut = '—';
			let tone = 'neutral';
			if (hasAnomaly) {
				({ label: statut, tone } = severityToStatus('warning'));
			} else if (eq === true) {
				statut = 'Conforme';
				tone = 'ok';
			} else if (eq === false) {
				statut = 'Attention';
				tone = 'warning';
			}
			return {
				code: 'incoterm_mismatch',
				categorie: 'Incoterm / livraison',
				dumValue: formatScalar(incotermDum),
				factureValue: formatScalar(incotermInv),
				ecart: '—',
				statut,
				tone,
			};
		},
		numero_declaration: () => ({
			code: 'numero_declaration',
			categorie: 'N° déclaration DUM',
			dumValue: formatScalar(numDecl),
			factureValue: formatScalar(invoiceMeta?.numero_facture || invoiceResult?.numero_facture),
			ecart: '—',
			statut: numDecl ? 'Conforme' : '—',
			tone: numDecl ? 'ok' : 'neutral',
		}),
	};

	return FIXED_ROW_ORDER.map((code) => rowBuilders[code]()).filter(Boolean);
};

export { formatMoney };
