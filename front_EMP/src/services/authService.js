import apiClient, { setToken, clearToken } from './api';

export const login = async ({ email, password }) => {
	const { data } = await apiClient.post('/auth/login', { email, password });
	if (data?.access_token) {
		setToken(data.access_token);
	}
	return data;
};

export const signup = async ({ fullName, email, password }) => {
	const payload = { username: fullName, email, password };
	const { data } = await apiClient.post('/auth/signup', payload);
	return data;
};

export const getMe = async () => {
	const { data } = await apiClient.get('/auth/me');
	return data;
};

export const logout = async () => {
	try {
		await apiClient.post('/auth/logout');
	} finally {
		clearToken();
	}
};

export const requestPasswordReset = async (email) => {
	const { data } = await apiClient.post('/auth/forgot-password', { email });
	return data;
};

export const confirmPasswordReset = async ({ token, newPassword }) => {
	const payload = { token, new_password: newPassword };
	const { data } = await apiClient.post('/auth/reset-password', payload);
	return data;
};
