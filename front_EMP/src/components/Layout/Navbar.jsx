import { NavLink } from 'react-router-dom';
import { LogOut, ShieldCheck, User as UserIcon } from 'lucide-react';
import empLogo from '../../assets/emp.png';
import { useAuth } from '../../hooks/useAuth';

const links = [
	{ to: '/', label: 'Accueil' },
	{ to: '/dashboard', label: 'Dashboard' },
	{ to: '/import', label: 'Import documents' },
	{ to: '/history', label: 'Historique' },
];

function Navbar() {
	const { isAuthenticated, user, logout } = useAuth();
	const roleLabel = user?.role === 'admin' ? 'Administrateur' : 'Utilisateur';
	const RoleIcon = user?.role === 'admin' ? ShieldCheck : UserIcon;

	const handleLogout = async () => {
		await logout();
	};

	return (
		<header className="navbar">
			<div className="navbar-brand">
				<img src={empLogo} alt="EMP" className="navbar-logo" />
				<div>
					<p className="navbar-title">EMP SmartOCR</p>
					<p className="navbar-tagline">Automate customs intelligence</p>
				</div>
			</div>
			<nav className="navbar-links">
				{links.map((link) => (
					<NavLink
						key={link.to}
						to={link.to}
						className={({ isActive }) => `navbar-link ${isActive ? 'active' : ''}`}
						end={link.to === '/'}
					>
						{link.label}
					</NavLink>
				))}
			</nav>
				{isAuthenticated && (
					<div className="navbar-right">
						<span className="role-badge">
							<RoleIcon size={16} /> {roleLabel}
						</span>
						<span className="user-email">{user?.email || 'user@example.com'}</span>
						<button className="logout-btn" onClick={handleLogout}>
							<LogOut size={16} />
							Logout
						</button>
					</div>
				)}
		</header>
	);
}

export default Navbar;
