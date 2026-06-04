const LAST_TYPE_KEY = 'emp_last_extraction_type';

const safeParse = (key) => {
	try {
		const raw = localStorage.getItem(key);
		return raw ? JSON.parse(raw) : null;
	} catch {
		return null;
	}
};

export const setLastExtractionType = (type) => {
	if (type === 'invoice' || type === 'declaration') {
		sessionStorage.setItem(LAST_TYPE_KEY, type);
	}
};

export const getLastExtractionType = () => sessionStorage.getItem(LAST_TYPE_KEY);

const INVOICE_NAME_RE = /facture|invoice|fa\d{5,}/i;
const DUM_NAME_RE = /dum|declaration|douane|customs/i;

/** Indice depuis le nom de fichier (Import). */
export const looksLikeInvoiceFileName = (name = '') => INVOICE_NAME_RE.test(String(name));

export const looksLikeDumFileName = (name = '') => DUM_NAME_RE.test(String(name));

const INVOICE_FIELD_KEYS = new Set([
	'numero_facture',
	'net_pay',
	'client_nom',
	'montant_brut',
	'montant_ttc',
]);

/** Détecte si le payload stocké correspond à une facture (et non une DUM). */
export const isInvoiceExtractionPayload = (saved) => {
	if (!saved || typeof saved !== 'object') {
		return false;
	}
	if (saved.selectedType === 'invoice') {
		return true;
	}
	const raw = saved.rawResult;
	if (raw && (raw.numero_facture != null || raw.net_pay != null || raw.fichier_nom)) {
		return true;
	}
	if (saved.invoiceId != null) {
		return true;
	}
	const fields = Array.isArray(saved.fields) ? saved.fields : [];
	return fields.some((f) => INVOICE_FIELD_KEYS.has(f?.key));
};

export const isDumExtractionPayload = (saved) => {
	if (!saved || typeof saved !== 'object') {
		return false;
	}
	if (saved.selectedType === 'declaration') {
		return true;
	}
	if (isInvoiceExtractionPayload(saved)) {
		return false;
	}
	const fields = Array.isArray(saved.fields) ? saved.fields : [];
	return fields.some((f) =>
		['numero_declaration', 'exportateur_nom', 'montant_ptfn', 'pfn'].includes(f?.key)
	);
};

export const getExtractionTimestamps = () => {
	const invoice = safeParse('invoice_latest_result');
	const dum = safeParse('ocr_latest_result');
	return {
		invoiceAt: invoice?.savedAt ? Date.parse(invoice.savedAt) : 0,
		dumAt: dum?.savedAt ? Date.parse(dum.savedAt) : 0,
		invoice,
		dum,
	};
};

/** Page résultats à afficher selon la dernière extraction réussie. */
export const resolveResultsRoute = () => {
	const last = getLastExtractionType();
	const { invoiceAt, dumAt, invoice, dum } = getExtractionTimestamps();

	if (last === 'invoice' && invoice) {
		return '/invoice-ocr-result';
	}
	if (last === 'declaration' && dum) {
		return '/ocr-result';
	}
	if (invoiceAt > dumAt && invoice) {
		return '/invoice-ocr-result';
	}
	if (dumAt > invoiceAt && dum) {
		return '/ocr-result';
	}
	if (invoice && isInvoiceExtractionPayload(invoice)) {
		return '/invoice-ocr-result';
	}
	if (dum) {
		return '/ocr-result';
	}
	return null;
};
