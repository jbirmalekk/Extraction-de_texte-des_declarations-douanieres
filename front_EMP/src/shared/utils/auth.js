const TOKEN_KEY = 'emp_token';

export const setToken = (token) => {
	localStorage.setItem(TOKEN_KEY, token);
};

export const getToken = () => localStorage.getItem(TOKEN_KEY);

export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export const isAuthenticated = () => Boolean(getToken());

export const authHeader = () => {
	const token = getToken();
	return token ? { Authorization: `Bearer ${token}` } : {};
};
