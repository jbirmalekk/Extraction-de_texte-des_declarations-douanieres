import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
	baseURL: API_BASE_URL,
	withCredentials: true,
	headers: {
		'Content-Type': 'application/json',
	},
});

let isRefreshing = false;
let refreshWaiters = [];

const queueRefreshWaiter = (resolve, reject) => {
	refreshWaiters.push({ resolve, reject });
};

const resolveRefreshWaiters = (error = null) => {
	refreshWaiters.forEach(({ resolve, reject }) => {
		if (error) {
			reject(error);
			return;
		}
		resolve();
	});
	refreshWaiters = [];
};

apiClient.interceptors.response.use(
	(response) => response,
	async (error) => {
		const originalRequest = error?.config;
		const status = error?.response?.status;
		const isAuthEndpoint = originalRequest?.url?.includes('/auth/login') || originalRequest?.url?.includes('/auth/refresh');
		if (status !== 401 || !originalRequest || originalRequest._retry || isAuthEndpoint) {
			return Promise.reject(error);
		}

		originalRequest._retry = true;
		if (isRefreshing) {
			return new Promise((resolve, reject) => {
				queueRefreshWaiter(
					() => resolve(apiClient(originalRequest)),
					(err) => reject(err),
				);
			});
		}

		isRefreshing = true;
		try {
			await apiClient.post('/auth/refresh');
			resolveRefreshWaiters();
			return apiClient(originalRequest);
		} catch (refreshError) {
			resolveRefreshWaiters(refreshError);
			return Promise.reject(refreshError);
		} finally {
			isRefreshing = false;
		}
	},
);

export const healthCheck = async () => {
	const { data } = await apiClient.get('/health');
	return data;
};

export default apiClient;
