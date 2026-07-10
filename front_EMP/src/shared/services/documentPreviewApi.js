import apiClient from '@/shared/services/api';
import { INVOICE_LIST_TIMEOUT_MS, invoiceApiClient } from '@/shared/services/invoiceApi';

const PREVIEW_FILE_TIMEOUT_MS = INVOICE_LIST_TIMEOUT_MS;

const normalizeAxiosBlobError = async (error) => {
	const data = error?.response?.data;
	if (data instanceof Blob) {
		try {
			const text = await data.text();
			const parsed = JSON.parse(text);
			error.response.data = parsed;
		} catch (parseError) {
			try {
				const fallbackText = await data.text();
				error.response.data = { detail: fallbackText?.slice(0, 500) || 'Erreur serveur' };
			} catch {
				error.response.data = { detail: 'Erreur serveur' };
			}
			void parseError;
		}
	}
	return error;
};

const blobToDataUrl = (blob) =>
	new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(reader.result);
		reader.onerror = () => reject(new Error('Impossible de lire le fichier.'));
		reader.readAsDataURL(blob);
	});

const buildPreviewFromBlob = async (blob, { name, type, responseHeaders }) => {
	const headerType = responseHeaders?.['content-type'] || responseHeaders?.['Content-Type'];
	const contentType = (type || headerType || blob.type || 'application/octet-stream').split(';')[0].trim();
	// Object URL : plus fiable que data:… en iframe PDF (DUM/factures depuis l'historique).
	const objectUrl = URL.createObjectURL(blob);
	return {
		name: name || 'document',
		type: contentType,
		dataUrl: objectUrl,
		isBlobUrl: true,
	};
};

/** Convertit un blob en data URL (snapshots / sessionStorage uniquement). */
export const blobPreviewToDataUrl = async (preview) => {
	if (!preview?.isBlobUrl || !preview?.dataUrl) {
		return preview;
	}
	const response = await fetch(preview.dataUrl);
	const blob = await response.blob();
	const dataUrl = await blobToDataUrl(blob);
	return { ...preview, dataUrl, isBlobUrl: false };
};

/**
 * Télécharge le fichier source DUM depuis back_EMP (Nextcloud / GED).
 * @param {number} documentId
 * @param {{ name?: string, type?: string }} [meta]
 */
export const fetchDumSourcePreview = async (documentId, meta = {}) => {
	const id = Number(documentId);
	if (!Number.isFinite(id) || id <= 0) {
		throw new Error('Identifiant document invalide.');
	}
	let response;
	try {
		response = await apiClient.get(`/api/documents/${id}/file`, {
			responseType: 'blob',
			timeout: PREVIEW_FILE_TIMEOUT_MS,
		});
	} catch (error) {
		throw await normalizeAxiosBlobError(error);
	}
	const { data, headers } = response;
	return buildPreviewFromBlob(data, {
		name: meta.name || `document_${id}`,
		type: meta.type,
		responseHeaders: headers,
	});
};

/**
 * Télécharge le fichier source facture depuis back_EMP_Fact.
 * @param {number} invoiceId
 * @param {{ name?: string, type?: string }} [meta]
 */
export const fetchInvoiceSourcePreview = async (invoiceId, meta = {}) => {
	const id = Number(invoiceId);
	if (!Number.isFinite(id) || id <= 0) {
		throw new Error('Identifiant facture invalide.');
	}
	let invResponse;
	try {
		invResponse = await invoiceApiClient.get(`/api/invoices/${id}/file`, {
			responseType: 'blob',
			timeout: PREVIEW_FILE_TIMEOUT_MS,
		});
	} catch (error) {
		throw await normalizeAxiosBlobError(error);
	}
	const { data, headers } = invResponse;
	return buildPreviewFromBlob(data, {
		name: meta.name || `facture_${id}`,
		type: meta.type,
		responseHeaders: headers,
	});
};
