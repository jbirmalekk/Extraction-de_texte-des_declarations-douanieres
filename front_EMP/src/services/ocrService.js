import apiClient from './api';

const buildClientPcName = () => {
	if (typeof window === 'undefined') {
		return 'unknown-client';
	}

	const host = window.location.hostname || '';
	const platform = window.navigator?.platform || '';
	const userAgentDataPlatform = window.navigator?.userAgentData?.platform || '';

	const candidateHost = host && host !== 'localhost' && host !== '127.0.0.1' ? host : '';
	return [candidateHost || 'browser-client', userAgentDataPlatform || platform]
		.filter(Boolean)
		.join(' | ')
		.slice(0, 255);
};

export const extractOcrDocument = async (
	file,
	{ fastMode = false, useDeskew = true, onUploadProgress, clientPcName } = {}
) => {
	const formData = new FormData();
	formData.append('file', file);

	const { data } = await apiClient.post('/api/ocr', formData, {
		params: {
			fast_mode: fastMode,
			use_deskew: useDeskew,
		},
		headers: {
			'Content-Type': 'multipart/form-data',
			'X-Client-PC-Name': clientPcName || buildClientPcName(),
		},
		onUploadProgress,
	});

	return data;
};

export const validateOcrDocument = async (documentId, payload) => {
	const { data } = await apiClient.put(`/api/ocr/${documentId}/valider`, payload);
	return data;
};

export const fetchLatestOcrCorrections = async (documentId) => {
	const { data } = await apiClient.get(`/api/ocr/${documentId}/corrections/latest`);
	return data;
};

/** Timeline complète des corrections d'un document DUM. */
export const fetchDocumentCorrections = async (documentId) => {
	const { data } = await apiClient.get(`/api/ocr/${documentId}/corrections`);
	return data;
};

export const fetchMyDashboard = async () => {
	const { data } = await apiClient.get('/api/dashboard/me');
	return data;
};

export const fetchAdminDashboard = async () => {
	const { data } = await apiClient.get('/api/dashboard/admin');
	return data;
};

/**
 * @param {{ skip?: number, limit?: number }} [params]
 */
export const fetchAdminHistory = async (params = {}) => {
	const { data } = await apiClient.get('/api/dashboard/history', { params });
	return data;
};

/**
 * @param {{ skip?: number, limit?: number }} [params]
 */
export const fetchMyHistory = async (params = {}) => {
	const { data } = await apiClient.get('/api/dashboard/me/history', { params });
	return data;
};

export const fetchDocumentDetail = async (documentId) => {
	const { data } = await apiClient.get(`/api/documents/${documentId}`);
	return data;
};

/**
 * Liste des DUM (documents) pour sélection partenaire réconciliation.
 * @param {{ skip?: number, limit?: number }} [params]
 */
export const fetchOcrDocuments = async (params = {}) => {
	const { data } = await apiClient.get('/api/documents', { params });
	return data;
};

/** Supprime une ou plusieurs DUM (base + fichier local). */
export const bulkDeleteDocuments = async (ids) => {
	const { data } = await apiClient.post('/api/documents/bulk-delete', { ids });
	return data;
};
