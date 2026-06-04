/**
 * Lit la dernière DUM extraite (localStorage) pour préremplir la comparaison facture.
 */

const safeParse = (value) => {
	if (!value) {
		return null;
	}
	try {
		return JSON.parse(value);
	} catch {
		return null;
	}
};

const parseAmount = (raw) => {
	if (raw == null || raw === '') {
		return null;
	}
	const n = Number(String(raw).replace(/\s/g, '').replace(',', '.'));
	return Number.isFinite(n) ? n : null;
};

const fieldValue = (saved, key) => {
	const fields = saved?.fields;
	if (Array.isArray(fields)) {
		const hit = fields.find((f) => f.key === key);
		if (hit?.value != null && String(hit.value).trim() !== '') {
			return String(hit.value).trim();
		}
	}
	const raw = saved?.rawResult;
	if (raw && raw[key] != null && String(raw[key]).trim() !== '') {
		return String(raw[key]).trim();
	}
	return null;
};

/**
 * @returns {null | {
 *   numero_declaration: string | null,
 *   montant_pfn: number | null,
 *   montant_ptfn: number | null,
 *   devise: string | null,
 *   valeur_dinars: number | null,
 *   nombre_colis: number | null,
 *   poids_net_kg: number | null,
 *   incoterm: string | null,
 *   documentId: string | null,
 * }}
 */
export const getDumSnapshotFromStorage = () => {
	const saved = safeParse(localStorage.getItem('ocr_latest_result'));
	if (!saved) {
		return null;
	}

	const pfnRaw =
		fieldValue(saved, 'pfn') ||
		fieldValue(saved, 'montant_ptfn') ||
		saved?.rawResult?.pfn ||
		saved?.rawResult?.montant_ptfn;

	const montantPfn = parseAmount(pfnRaw);

	const backendId =
		saved?.backendId ??
		saved?.rawResult?.id ??
		saved?.rawResult?.document_id ??
		null;

	return {
		dum_document_id: backendId != null ? Number(backendId) : null,
		numero_declaration: fieldValue(saved, 'numero_declaration'),
		montant_pfn: montantPfn,
		montant_ptfn: montantPfn,
		devise: fieldValue(saved, 'devise'),
		valeur_dinars: parseAmount(fieldValue(saved, 'valeur_dinars')),
		nombre_colis: parseAmount(fieldValue(saved, 'nombre_colis')),
		poids_net_kg: parseAmount(fieldValue(saved, 'poids_net')),
		incoterm: fieldValue(saved, 'mode_livraison'),
		documentId: saved.documentId || null,
	};
};

export const hasDumSnapshot = () => {
	const snap = getDumSnapshotFromStorage();
	return Boolean(snap?.dum_document_id || snap?.numero_declaration || snap?.montant_pfn);
};
