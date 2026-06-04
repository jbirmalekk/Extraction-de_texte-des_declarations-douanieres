import axios from 'axios';
import apiClient from './api';

/** Serveur S2 — migration ERP (exemple : localhost:8002). */
export const ERP_API_BASE_URL =
	import.meta.env.VITE_ERP_API_URL || 'http://localhost:8002';

const erpClient = axios.create({
	baseURL: ERP_API_BASE_URL,
	headers: { 'Content-Type': 'application/json' },
	withCredentials: false,
});

/**
 * Étape 1 — S1 : enregistrer le JSON d'intégration en base OCR.
 * @returns {{ export_id, kind, status, reference, payload }}
 */
export const postErpValidationData = async ({
	kind,
	dumDocumentId = null,
	invoiceId = null,
	reference = null,
}) => {
	const { data } = await apiClient.post('/api/erp/validation-data', {
		kind,
		dum_document_id: dumDocumentId,
		invoice_id: invoiceId,
		reference,
	});
	return data;
};

/**
 * Étape 2 — S2 : migration ERP (lit le JSON sur S1 via export_id).
 */
export const postErpMigration = async (exportId) => {
	const { data } = await erpClient.post('/api/migration', { export_id: exportId });
	return data;
};

export const checkErpServiceHealth = async () => {
	const { data } = await erpClient.get('/health');
	return data;
};
