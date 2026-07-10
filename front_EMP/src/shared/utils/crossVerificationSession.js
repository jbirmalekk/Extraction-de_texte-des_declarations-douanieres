const STORAGE_KEY = 'cross_verification_session';

export const saveCrossVerificationSession = (session) => {
	const payload = {
		...session,
		savedAt: new Date().toISOString(),
	};
	localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
	return payload;
};

export const getCrossVerificationSession = () => {
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		return raw ? JSON.parse(raw) : null;
	} catch {
		return null;
	}
};

export const updateCrossVerificationSession = (patch) => {
	const current = getCrossVerificationSession() || {};
	const next = saveCrossVerificationSession({ ...current, ...patch });
	return next;
};

export const clearCrossVerificationSession = () => {
	localStorage.removeItem(STORAGE_KEY);
};

/** Nouvelle réconciliation : source seule, sans partenaire ni comparaison précédente. */
export const beginReconciliationSession = ({
	sourceType,
	sourceId,
	sourceNumero,
	sourceDate = null,
	sourceLabel,
	sourceFileName,
}) =>
	saveCrossVerificationSession({
		sourceType,
		sourceId,
		sourceNumero: sourceNumero ?? null,
		sourceDate,
		sourceLabel: sourceLabel ?? sourceNumero ?? null,
		sourceFileName: sourceFileName ?? sourceLabel ?? null,
		redoReconciliation: true,
		partnerType: null,
		partnerId: null,
		comparisonResult: null,
		invoiceId: null,
		dumDocumentId: null,
		dumPreview: null,
		invoicePreview: null,
		pendingPartnerId: null,
	});

const IMPORT_RETURN_KEY = 'emp_cross_verify_import_return';

/** Mémorise un retour vers la réconciliation après import du document partenaire. */
export const markCrossVerifyImportReturn = (partnerKind) => {
	sessionStorage.setItem(IMPORT_RETURN_KEY, partnerKind === 'invoice' ? 'invoice' : 'dum');
};

export const peekCrossVerifyImportReturn = () => {
	const kind = sessionStorage.getItem(IMPORT_RETURN_KEY);
	return kind === 'invoice' || kind === 'dum' ? kind : null;
};

export const consumeCrossVerifyImportReturn = () => {
	const kind = peekCrossVerifyImportReturn();
	sessionStorage.removeItem(IMPORT_RETURN_KEY);
	return kind;
};
