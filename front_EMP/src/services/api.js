import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const TOKEN_KEY = 'emp_token';

export const apiClient = axios.create({
	baseURL: API_BASE_URL,
	headers: {
		'Content-Type': 'application/json',
	},
});

apiClient.interceptors.request.use((config) => {
	const token = localStorage.getItem(TOKEN_KEY);
	if (token) {
		config.headers.Authorization = `Bearer ${token}`;
	}
	return config;
});

export const setToken = (token) => {
	localStorage.setItem(TOKEN_KEY, token);
};

export const clearToken = () => {
	localStorage.removeItem(TOKEN_KEY);
};

export const getToken = () => localStorage.getItem(TOKEN_KEY);

export const healthCheck = async () => {
	const { data } = await apiClient.get('/health');
	return data;
};

export default apiClient;
