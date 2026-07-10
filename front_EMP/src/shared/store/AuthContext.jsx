import { createContext, useCallback, useEffect, useMemo, useState } from 'react';
import { getMe, login as loginService, logout as logoutService, logoutAllSessions as logoutAllService } from '../services/authService';

export const AuthContext = createContext({
	user: null,
	loading: true,
	isAuthenticated: false,
	login: async () => {},
	logout: async () => {},
	logoutAllSessions: async () => {},
	refreshUser: async () => {},
});

export function AuthProvider({ children }) {
	const [user, setUser] = useState(null);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		const bootstrap = async () => {
			try {
				const me = await getMe();
				setUser(me);
			} catch (error) {
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
		let me = null;
		try {
			me = await refreshUser();
		} catch (error) {
			setUser(null);
		}
		return { ...data, user: me };
	}, [refreshUser]);

	const logout = useCallback(async () => {
		try {
			await logoutService();
		} catch (error) {
			// Even if the API fails, clear local auth state.
		} finally {
			setUser(null);
		}
	}, []);

	const logoutAllSessions = useCallback(async () => {
		try {
			await logoutAllService();
		} finally {
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
			logoutAllSessions,
			refreshUser,
		}),
		[user, loading, login, logout, logoutAllSessions, refreshUser],
	);

	return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
