import apiClient from './api';

/**
 * Historique unifié (back_EMP) — DUM et factures si INVOICE_API_URL configurée.
 * @param {{ type?: 'dum'|'invoice'|'all', skip?: number, limit?: number }} params
 */
export const fetchUnifiedHistoryApi = async (params = {}) => {
	const { data } = await apiClient.get('/api/history', {
		params: {
			type: params.type ?? 'all',
			skip: params.skip ?? 0,
			limit: params.limit ?? 50,
		},
	});
	return data;
};
