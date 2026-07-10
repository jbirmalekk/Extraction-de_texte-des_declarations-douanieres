import { fetchDumSourcePreview, fetchInvoiceSourcePreview } from '@/shared/services/documentPreviewApi';
import { fetchInvoiceById } from '@/shared/services/invoiceApi';
import { fetchDocumentDetail } from '@/shared/services/ocrService';
import { resolveStoredDocumentPreview } from '@/shared/utils/compareDocumentPreview';
import { writeSessionDocumentPreview } from '@/shared/utils/documentPreviewCache';
import { mapInvoiceBackendToFields } from '@/shared/utils/invoiceFields';
import { mapBackendResultToFields } from '@/shared/utils/ocrFields';

const persistJson = (key, payload) => {
	try {
		localStorage.setItem(key, JSON.stringify(payload));
		return true;
	} catch (error) {
		console.warn(`Impossible de sauvegarder ${key} dans localStorage`, error);
		return false;
	}
};

/** Ne pas stocker dataUrl (plusieurs Mo) dans localStorage — quota ~5 Mo. */
export const stripPreviewForLocalStorage = (source) => {
	if (!source?.dataUrl) {
		return source;
	}
	const { dataUrl: _drop, isBlobUrl: _blob, ...meta } = source;
	return Object.keys(meta).length ? meta : null;
};

export const slimDocumentForStorage = (doc) => {
	if (!doc || typeof doc !== 'object') {
		return doc;
	}
	const { texte_brut, uploaded_by, articles, taxes, ...rest } = doc;
	return {
		...rest,
		texte_brut: typeof texte_brut === 'string' ? texte_brut.slice(0, 500) : texte_brut,
	};
};

/** Payload validation sans binaire (localStorage-safe). */
export const prepareValidationPayloadForStorage = (payload) => {
	if (!payload || typeof payload !== 'object') {
		return payload;
	}
	const source = payload.source
		? stripPreviewForLocalStorage(payload.source) || {
				name: payload.source.name || 'document',
				type: payload.source.type || 'application/pdf',
			}
		: payload.source;
	return {
		...payload,
		source,
		rawResult: slimDocumentForStorage(payload.rawResult),
	};
};

const cachePreviewForEntity = (kind, entityId, preview) => {
	const id = Number(entityId);
	if (!preview?.dataUrl || !Number.isFinite(id) || id <= 0) {
		return;
	}
	// blob: URLs expirent — seuls les data: (petits) vont en sessionStorage.
	if (preview.isBlobUrl || preview.dataUrl.startsWith('blob:')) {
		return;
	}
	if (preview.dataUrl.length > 800_000) {
		return;
	}
	try {
		writeSessionDocumentPreview(kind, id, preview);
	} catch (error) {
		console.warn(`Aperçu non mis en cache session (${kind} #${id})`, error);
	}
};

/** Page résultats OCR → validation DUM (sans dataUrl dans localStorage). */
export const saveDumValidationPayload = ({
	documentId,
	backendId,
	fields,
	modifiedFields,
	preview = null,
	rawResult = null,
}) => {
	const payload = prepareValidationPayloadForStorage({
		documentId,
		backendId,
		fields,
		modifiedFields,
		savedAt: new Date().toISOString(),
		source: preview,
		rawResult,
	});
	cachePreviewForEntity('dum', backendId, preview);
	const ok = persistJson('ocr_validation_payload', payload);
	if (ok) {
		persistJson('ocr_latest_result', {
			...payload,
			selectedType: 'declaration',
		});
	}
	return { ok, payload };
};

/** Page résultats OCR → validation facture (sans dataUrl dans localStorage). */
export const saveInvoiceValidationPayload = ({
	documentId,
	backendId,
	invoiceId,
	fields,
	modifiedFields,
	preview = null,
	rawResult = null,
}) => {
	const id = invoiceId ?? backendId;
	const payload = prepareValidationPayloadForStorage({
		documentId,
		backendId: id,
		invoiceId: id,
		fields,
		modifiedFields,
		savedAt: new Date().toISOString(),
		source: preview,
		rawResult,
	});
	cachePreviewForEntity('invoice', id, preview);
	const ok = persistJson('invoice_validation_payload', payload);
	if (ok) {
		persistJson('invoice_latest_result', {
			...payload,
			selectedType: 'invoice',
		});
	}
	return { ok, payload };
};

/** Métadonnées seulement — pas de dataUrl cache ici (évite une mauvaise image d'un autre document). */
const buildPreviewMeta = (_kind, _id, fileName, contentType) => ({
	name: fileName || 'document',
	type: contentType || 'application/pdf',
});

export const buildDumContextFromDocument = (doc) => {
	const backendId = doc?.id;
	const documentId = doc?.numero_declaration || (backendId != null ? `Document #${backendId}` : 'Document');
	const fields = mapBackendResultToFields(doc, { useDemoFallback: false });
	const source = buildPreviewMeta('dum', backendId, doc?.fichier, 'application/pdf');
	const savedAt = new Date().toISOString();

	const latestResult = {
		documentId,
		backendId,
		fields,
		rawResult: doc,
		selectedType: 'declaration',
		savedAt,
		source,
	};

	const validationPayload = {
		documentId,
		backendId,
		fields,
		modifiedFields: {},
		savedAt,
		source,
		rawResult: doc,
	};

	return { latestResult, validationPayload };
};

export const buildInvoiceContextFromRecord = (inv) => {
	const invoiceId = inv?.id;
	const documentId = inv?.numero_facture || (invoiceId != null ? `FACT-${invoiceId}` : 'Facture');
	const fields = mapInvoiceBackendToFields(inv, { onlyPopulated: false, includeControleDum: true });
	const source = buildPreviewMeta(
		'invoice',
		invoiceId,
		inv?.fichier_nom || inv?.fichier_source || inv?.fichier,
		inv?.content_type || 'application/pdf'
	);
	const savedAt = new Date().toISOString();

	const latestResult = {
		invoiceId,
		backendId: invoiceId,
		documentId,
		fields,
		rawResult: inv,
		selectedType: 'invoice',
		savedAt,
		source,
	};

	const validationPayload = {
		documentId,
		invoiceId,
		backendId: invoiceId,
		fields,
		modifiedFields: {},
		savedAt,
		source,
		rawResult: inv,
	};

	return { latestResult, validationPayload };
};

const mergeStoredPreview = (kind, entityId, source) => {
	const id = Number(entityId);
	if (!Number.isFinite(id) || id <= 0) {
		return source;
	}
	const stored = resolveStoredDocumentPreview(kind, id);
	if (stored?.dataUrl) {
		return stored;
	}
	return source;
};

const attachPreviewFromApi = async (kind, entityId, source, fileName, contentType) => {
	const id = Number(entityId);
	if (!Number.isFinite(id) || id <= 0) {
		return source;
	}
	const meta = {
		name: fileName || source?.name || 'document',
		type: contentType || source?.type || 'application/pdf',
	};
	try {
		const remote =
			kind === 'invoice'
				? await fetchInvoiceSourcePreview(id, { name: meta.name, type: meta.type })
				: await fetchDumSourcePreview(id, { name: meta.name, type: meta.type });
		return remote;
	} catch (err) {
		const status = err?.response?.status;
		const detail =
			typeof err?.response?.data?.detail === 'string'
				? err.response.data.detail
				: null;
		const unavailable =
			status === 404
				? detail ||
					'Fichier source absent sur le serveur (document ancien). Réimportez le PDF depuis Import.'
				: detail || null;
		const merged = mergeStoredPreview(kind, id, meta);
		if (unavailable && !merged?.dataUrl) {
			return { ...merged, previewUnavailable: unavailable };
		}
		return merged;
	}
};

/** Charge une DUM depuis l'API et synchronise localStorage (résultats + validation). */
export const hydrateDumContextFromApi = async (documentId) => {
	const doc = await fetchDocumentDetail(documentId);
	const { latestResult, validationPayload } = buildDumContextFromDocument(doc);
	let source = await attachPreviewFromApi(
		'dum',
		documentId,
		validationPayload.source,
		doc?.fichier,
		'application/pdf'
	);
	source = mergeStoredPreview('dum', documentId, source);
	if (source?.dataUrl && !source?.isBlobUrl) {
		writeSessionDocumentPreview('dum', documentId, source);
	}
	const sourceForStorage = stripPreviewForLocalStorage(source);
	const slimDoc = slimDocumentForStorage(doc);
	latestResult.source = sourceForStorage;
	validationPayload.source = sourceForStorage;
	latestResult.rawResult = slimDoc;
	validationPayload.rawResult = slimDoc;
	persistJson('ocr_latest_result', latestResult);
	persistJson('ocr_validation_payload', validationPayload);
	return { ...latestResult, source };
};

/** Charge une facture depuis l'API et synchronise localStorage. */
export const hydrateInvoiceContextFromApi = async (invoiceId) => {
	const inv = await fetchInvoiceById(invoiceId);
	const { latestResult, validationPayload } = buildInvoiceContextFromRecord(inv);
	let source = await attachPreviewFromApi(
		'invoice',
		invoiceId,
		validationPayload.source,
		inv?.fichier_nom,
		inv?.content_type || 'application/pdf'
	);
	source = mergeStoredPreview('invoice', invoiceId, source);
	if (source?.dataUrl && !source?.isBlobUrl) {
		writeSessionDocumentPreview('invoice', invoiceId, source);
	}
	const sourceForStorage = stripPreviewForLocalStorage(source);
	const slimInv = slimDocumentForStorage(inv);
	latestResult.source = sourceForStorage;
	validationPayload.source = sourceForStorage;
	latestResult.rawResult = slimInv;
	validationPayload.rawResult = slimInv;
	persistJson('invoice_latest_result', latestResult);
	persistJson('invoice_validation_payload', validationPayload);
	return { ...latestResult, source };
};

export const cacheDocumentPreview = (kind, entityId, preview) => {
	if (!preview?.dataUrl || preview?.isBlobUrl) {
		return;
	}
	const id = Number(entityId);
	if (!Number.isFinite(id) || id <= 0) {
		return;
	}
	writeSessionDocumentPreview(kind, id, preview);
};

/** Aligne ocr_latest_result sur le document de la validation en cours. */
export const syncDumLatestFromValidationPayload = async () => {
	const payload = JSON.parse(localStorage.getItem('ocr_validation_payload') || 'null');
	if (!payload?.backendId) {
		return null;
	}
	let source = payload.source || null;
	if (!source?.dataUrl) {
		source = await attachPreviewFromApi(
			'dum',
			payload.backendId,
			source,
			payload.rawResult?.fichier || source?.name,
			source?.type || 'application/pdf'
		);
	}
	const latest = {
		documentId: payload.documentId,
		backendId: payload.backendId,
		fields: payload.fields || [],
		modifiedFields: payload.modifiedFields || {},
		selectedType: 'declaration',
		savedAt: payload.savedAt || new Date().toISOString(),
		source,
		rawResult: payload.rawResult || null,
	};
	const sourceForStorage = stripPreviewForLocalStorage(source);
	const nextPayload = { ...payload, source: sourceForStorage };
	const nextLatest = { ...latest, source: sourceForStorage };
	persistJson('ocr_latest_result', nextLatest);
	persistJson('ocr_validation_payload', nextPayload);
	if (source?.dataUrl) {
		cacheDocumentPreview('dum', payload.backendId, source);
	}
	return { ...nextLatest, source };
};

/** Aligne invoice_latest_result sur la facture de la validation en cours. */
export const syncInvoiceLatestFromValidationPayload = async () => {
	const payload = JSON.parse(localStorage.getItem('invoice_validation_payload') || 'null');
	if (!payload?.invoiceId && !payload?.backendId) {
		return null;
	}
	const invoiceId = payload.invoiceId ?? payload.backendId;
	let source = payload.source || null;
	if (!source?.dataUrl) {
		source = await attachPreviewFromApi(
			'invoice',
			invoiceId,
			source,
			payload.rawResult?.fichier_nom || source?.name,
			payload.rawResult?.content_type || source?.type || 'application/pdf'
		);
	}
	const latest = {
		invoiceId,
		documentId: payload.documentId,
		backendId: invoiceId,
		fields: payload.fields || [],
		modifiedFields: payload.modifiedFields || {},
		selectedType: 'invoice',
		savedAt: payload.savedAt || new Date().toISOString(),
		source,
		rawResult: payload.rawResult || null,
	};
	const sourceForStorage = stripPreviewForLocalStorage(source);
	const nextPayload = { ...payload, source: sourceForStorage };
	const nextLatest = { ...latest, source: sourceForStorage };
	persistJson('invoice_latest_result', nextLatest);
	persistJson('invoice_validation_payload', nextPayload);
	if (source?.dataUrl) {
		cacheDocumentPreview('invoice', invoiceId, source);
	}
	return { ...nextLatest, source };
};
