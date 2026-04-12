import { createContext, useCallback, useEffect, useMemo, useState } from 'react';
import { clearToken, getToken } from '../services/api';
import { getMe, login as loginService, logout as logoutService } from '../services/authService';

export const AuthContext = createContext({
	user: null,
	loading: true,
	isAuthenticated: false,
	login: async () => {},
	logout: async () => {},
	refreshUser: async () => {},
});

export function AuthProvider({ children }) {
	const [user, setUser] = useState(null);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		const bootstrap = async () => {
			const token = getToken();
			if (!token) {
				setLoading(false);
				return;
			}

			try {
				const me = await getMe();
				setUser(me);
			} catch (error) {
				clearToken();
				setUser(null);
			} finally {
				setLoading(false);
			}
		};

		bootstrap();
	}, []);

	const refreshUser = useCallback(async () => {
		const me = await getMe();
		setUser(me);
		return me;
	}, []);

	const login = useCallback(async (credentials) => {
		const data = await loginService(credentials);
		try {
			await refreshUser();
		} catch (error) {
			setUser(null);
		}
		return data;
	}, [refreshUser]);

	const logout = useCallback(async () => {
		try {
			await logoutService();
		} catch (error) {
			// Even if the API fails, clear local auth state.
		} finally {
			clearToken();
			setUser(null);
		}
	}, []);

	const value = useMemo(
		() => ({
			user,
			loading,
			isAuthenticated: Boolean(user),
			login,
			logout,
			refreshUser,
		}),
		[user, loading, login, logout, refreshUser],
	);

	return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
