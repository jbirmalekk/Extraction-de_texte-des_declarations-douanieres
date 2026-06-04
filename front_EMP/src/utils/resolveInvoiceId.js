const safeParse = (key) => {
	try {
		const raw = localStorage.getItem(key);
		return raw ? JSON.parse(raw) : null;
	} catch {
		return null;
	}
};

/** ID facture (back_EMP_Fact) depuis payload validation ou dernier import. */
export const resolveInvoiceIdFromStorage = (payload = null) => {
	const fromPayload =
		payload?.rawResult?.id ?? payload?.backendId ?? payload?.invoiceId ?? null;
	if (fromPayload != null && fromPayload !== '') {
		const n = Number(fromPayload);
		if (Number.isFinite(n) && n > 0) {
			return n;
		}
	}

	const latest = safeParse('invoice_latest_result');
	const fromLatest = latest?.invoiceId ?? latest?.rawResult?.id ?? null;
	if (fromLatest != null) {
		const n = Number(fromLatest);
		if (Number.isFinite(n) && n > 0) {
			return n;
		}
	}

	return null;
};
