/**
 * Reconstruit un File depuis invoice_uploaded_document (localStorage).
 * @returns {Promise<File | null>}
 */
export const fileFromStoredInvoiceDocument = async () => {
	let stored = null;
	try {
		const raw = localStorage.getItem('invoice_uploaded_document');
		stored = raw ? JSON.parse(raw) : null;
	} catch {
		return null;
	}

	const dataUrl = stored?.dataUrl;
	if (!dataUrl || typeof dataUrl !== 'string') {
		return null;
	}

	const response = await fetch(dataUrl);
	const blob = await response.blob();
	const name = stored?.name || 'facture.pdf';
	const type = stored?.type || blob.type || 'application/pdf';
	return new File([blob], name, { type, lastModified: stored?.lastModified || Date.now() });
};
