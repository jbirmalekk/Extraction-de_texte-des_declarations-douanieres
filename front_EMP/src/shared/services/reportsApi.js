import apiClient from '@/shared/services/api';

/**
 * Liste légère des rapports de contrôle (back_EMP, SQL direct).
 * @param {{ skip?: number, limit?: number }} params
 */
export const fetchReportsSummary = async (params = {}) => {
	const { data } = await apiClient.get('/api/reports', {
		params: {
			skip: params.skip ?? 0,
			limit: params.limit ?? 30,
		},
	});
	return {
		items: data?.items ?? [],
		total: data?.total ?? 0,
		skip: data?.skip ?? 0,
		limit: data?.limit ?? 30,
	};
};
