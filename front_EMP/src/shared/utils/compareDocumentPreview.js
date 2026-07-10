import { fetchDumSourcePreview, fetchInvoiceSourcePreview } from '../services/documentPreviewApi';
import { readSessionDocumentPreview } from './documentPreviewCache';
import { getCrossVerificationSession } from './crossVerificationSession';

const safeParse = (key) => {
	try {
		const raw = localStorage.getItem(key);
		return raw ? JSON.parse(raw) : null;
	} catch {
		return null;
	}
};

const hasPreview = (doc) => Boolean(doc?.dataUrl && typeof doc.dataUrl === 'string');

const previewFromPayload = (payload, idField, targetId) => {
	if (!payload || Number(payload[idField]) !== Number(targetId)) {
		return null;
	}
	if (hasPreview(payload.source)) {
		return payload.source;
	}
	return null;
};

/**
 * Retrouve l'aperçu fichier (dataUrl) stocké localement pour une DUM ou une facture.
 * @param {'dum' | 'invoice'} kind
 * @param {number} documentId
 * @param {object} [session]
 */
export const resolveStoredDocumentPreview = (kind, documentId, session = null) => {
	const id = Number(documentId);
	if (!Number.isFinite(id) || id <= 0) {
		return null;
	}

	const sess = session ?? getCrossVerificationSession();

	if (kind === 'dum') {
		const fromSession = readSessionDocumentPreview('dum', id);
		if (fromSession) {
			return fromSession;
		}
		if (Number(sess?.dumDocumentId) === id && hasPreview(sess?.dumPreview)) {
			return sess.dumPreview;
		}
		if (sess?.sourceType === 'dum' && Number(sess?.sourceId) === id && hasPreview(sess?.sourcePreview)) {
			return sess.sourcePreview;
		}

		const fromValidation = previewFromPayload(safeParse('ocr_validation_payload'), 'backendId', id);
		if (fromValidation) {
			return fromValidation;
		}
		const latest = safeParse('ocr_latest_result');
		if (Number(latest?.backendId) === id) {
			if (hasPreview(latest?.source)) {
				return latest.source;
			}
		}
		const uploaded = safeParse('ocr_uploaded_document');
		if (hasPreview(uploaded) && Number(uploaded?.documentId) === id) {
			return uploaded;
		}
		return null;
	}

	const fromSession = readSessionDocumentPreview('invoice', id);
	if (fromSession) {
		return fromSession;
	}
	if (Number(sess?.invoiceId) === id && hasPreview(sess?.invoicePreview)) {
		return sess.invoicePreview;
	}
	if (sess?.sourceType === 'invoice' && Number(sess?.sourceId) === id && hasPreview(sess?.sourcePreview)) {
		return sess.sourcePreview;
	}

	const fromValidation = previewFromPayload(safeParse('invoice_validation_payload'), 'invoiceId', id);
	if (fromValidation) {
		return fromValidation;
	}
	const fromValidationBackend = previewFromPayload(safeParse('invoice_validation_payload'), 'backendId', id);
	if (fromValidationBackend) {
		return fromValidationBackend;
	}

	const latest = safeParse('invoice_latest_result');
	if (Number(latest?.invoiceId) === id || Number(latest?.backendId) === id) {
		if (hasPreview(latest?.source)) {
			return latest.source;
		}
	}
	const uploaded = safeParse('invoice_uploaded_document');
	if (hasPreview(uploaded) && Number(uploaded?.invoiceId) === id) {
		return uploaded;
	}
	return null;
};

export const snapshotPreview = (preview) => {
	if (!hasPreview(preview)) {
		return null;
	}
	return {
		name: preview.name || 'document',
		type: preview.type || 'application/pdf',
		dataUrl: preview.dataUrl,
	};
};

/**
 * Aperçu local puis téléchargement GED (Nextcloud) si nécessaire.
 * @param {{ dumId: number, invoiceId: number, session?: object, dumDoc?: object, invoice?: object }} opts
 */
export const loadCrossVerifyPreviews = async ({
	dumId,
	invoiceId,
	session = null,
	dumDoc = null,
	invoice = null,
}) => {
	const sess = session ?? getCrossVerificationSession();

	let dumPreview =
		resolveStoredDocumentPreview('dum', dumId, sess) ||
		(sess?.sourceType === 'dum' ? snapshotPreview(sess?.sourcePreview) : null);
	let invoicePreview =
		resolveStoredDocumentPreview('invoice', invoiceId, sess) ||
		(sess?.sourceType === 'invoice' ? snapshotPreview(sess?.sourcePreview) : null);

	const errors = { dum: '', invoice: '' };

	const [dumRemote, invoiceRemote] = await Promise.all([
		hasPreview(dumPreview)
			? Promise.resolve(null)
			: fetchDumSourcePreview(dumId, { name: dumDoc?.fichier }).catch((err) => {
					errors.dum = err?.message || 'Impossible de charger le fichier DUM.';
					return null;
				}),
		hasPreview(invoicePreview)
			? Promise.resolve(null)
			: fetchInvoiceSourcePreview(invoiceId, {
					name: invoice?.fichier_nom,
					type: invoice?.content_type,
				}).catch((err) => {
					errors.invoice = err?.message || 'Impossible de charger le fichier facture.';
					return null;
				}),
	]);

	if (hasPreview(dumRemote)) {
		dumPreview = dumRemote;
		errors.dum = '';
	}
	if (hasPreview(invoiceRemote)) {
		invoicePreview = invoiceRemote;
		errors.invoice = '';
	}

	if (!hasPreview(dumPreview) && !errors.dum) {
		errors.dum = !dumDoc?.dossier
			? 'Fichier DUM introuvable (aucun chemin GED en base). Réimportez la DUM.'
			: 'Impossible de charger le fichier DUM.';
	}
	if (!hasPreview(invoicePreview) && !errors.invoice) {
		errors.invoice = !invoice?.dossier
			? 'Fichier facture introuvable (aucun chemin GED en base). Réimportez la facture depuis Import.'
			: 'Impossible de charger le fichier facture.';
	}

	return { dumPreview, invoicePreview, errors };
};
