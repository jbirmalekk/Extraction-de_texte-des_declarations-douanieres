import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { LogOut, ShieldCheck, User as UserIcon } from 'lucide-react';
import empLogo from '@/assets/emp.png';
import { useAuth } from '@/shared/hooks/useAuth';

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
							<span className="app-brand-tagline">Intelligence douanière automatisée</span>
						</div>
					</div>
					<nav className="nav-links">
						<NavLink to="/dashboard" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
							Tableau de bord
						</NavLink>
						<NavLink to="/import" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
							Import
						</NavLink>
						<NavLink to="/history" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
							Historique
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
						Déconnexion
					</button>
				</div>
			</header>

			<Outlet />
		</div>
	);
}

export default AppLayout;