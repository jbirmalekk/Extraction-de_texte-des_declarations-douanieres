import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

function ProtectedRoute({ children, allowedRoles }) {
	const location = useLocation();
	const { isAuthenticated, loading, user } = useAuth();

	if (loading) {
		return (
			<div className="auth-container">
				<div className="auth-card">
					<p className="auth-subtitle">Checking your session...</p>
				</div>
			</div>
		);
	}

	if (!isAuthenticated) {
		return <Navigate to="/login" replace state={{ from: location }} />;
	}

	if (allowedRoles?.length && !allowedRoles.includes(user?.role)) {
		return <Navigate to="/dashboard" replace />;
	}

	return children || <Outlet />;
}

export default ProtectedRoute;
