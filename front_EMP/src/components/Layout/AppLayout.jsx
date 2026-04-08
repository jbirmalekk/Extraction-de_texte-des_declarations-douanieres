import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { LogOut, ShieldCheck, User as UserIcon } from 'lucide-react';
import empLogo from '../../assets/emp.png';
import { useAuth } from '../../hooks/useAuth';

function AppLayout() {
	const { user, logout } = useAuth();
	const navigate = useNavigate();
	const roleLabel = user?.role === 'admin' ? 'Administrateur' : 'Utilisateur';
	const RoleIcon = user?.role === 'admin' ? ShieldCheck : UserIcon;

	const handleLogout = async () => {
		await logout();
		navigate('/login');
	};

	return (
		<div className="dashboard-page">
			<header className="dashboard-nav">
				<div className="nav-left">
					<div className="app-brand">
						<img src={empLogo} alt="EMP" className="app-brand-logo" />
						<div className="app-brand-text">
							<span className="app-brand-title">EMP SmartOCR</span>
							<span className="app-brand-tagline">Automate customs intelligence</span>
						</div>
					</div>
					<nav className="nav-links">
						<NavLink to="/dashboard" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
							Dashboard
						</NavLink>
						<NavLink to="/import" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
							Import documents
						</NavLink>
						<NavLink to="/history" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
							History
						</NavLink>
					</nav>
				</div>
				<div className="nav-meta">
					<span className="role-badge">
						<RoleIcon size={16} /> {roleLabel}
					</span>
					<span className="user-email">{user?.email || 'user@example.com'}</span>
					<button className="logout-btn" onClick={handleLogout}>
						<LogOut size={16} />
						Logout
					</button>
				</div>
			</header>

			<Outlet />
		</div>
	);
}

export default AppLayout;