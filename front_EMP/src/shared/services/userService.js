import apiClient from '@/shared/services/api';

export const updateMyProfile = async ({ username, email }) => {
	const payload = {};
	if (typeof username === 'string') {
		payload.username = username;
	}
	if (typeof email === 'string') {
		payload.email = email;
	}

	const { data } = await apiClient.put('/auth/me', payload);
	return data;
};

export const changeMyPassword = async ({ currentPassword, newPassword }) => {
	const { data } = await apiClient.put('/auth/me/password', {
		current_password: currentPassword,
		new_password: newPassword,
	});
	return data;
};

export const verifyEmail = async (token) => {
	const { data } = await apiClient.post('/auth/verify-email', { token });
	return data;
};

export const listUsers = async () => {
	const { data } = await apiClient.get('/auth/users');
	return data;
};

export const getPendingUsers = async () => {
	const { data } = await apiClient.get('/auth/pending-users');
	return data;
};

export const getUserByAdmin = async (userId) => {
	const { data } = await apiClient.get(`/auth/users/${userId}`);
	return data;
};

export const updateUserByAdmin = async (userId, payload) => {
	const { data } = await apiClient.put(`/auth/users/${userId}`, payload);
	return data;
};

export const deleteUserByAdmin = async (userId) => {
	await apiClient.delete(`/auth/users/${userId}`);
};

export const approveUser = async (userId) => {
	const { data } = await apiClient.post(`/auth/approve-user/${userId}`);
	return data;
};

export const rejectUser = async (userId) => {
	const { data } = await apiClient.post(`/auth/reject-user/${userId}`);
	return data;
};
