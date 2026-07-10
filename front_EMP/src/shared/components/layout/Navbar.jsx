import { Link, NavLink, useLocation } from 'react-router-dom';
import { LogOut, ShieldCheck, User as UserIcon } from 'lucide-react';
import empLogo from '../../assets/emp.png';
import { useAuth } from '../../hooks/useAuth';

const publicLinks = [
	{ type: 'route', to: '/', label: 'Accueil' },
	{ type: 'hash', href: '/#details', label: 'Détails' },
	{ type: 'hash', href: '/#contact', label: 'Contact' },
];

const privateLinks = [
	{ type: 'route', to: '/dashboard', label: 'Tableau de bord' },
	{ type: 'hash', href: '/#details', label: 'Détails' },
	{ type: 'hash', href: '/#contact', label: 'Contact' },
];

function Navbar() {
	const { isAuthenticated, user, logout } = useAuth();
	const location = useLocation();
	const dashboardLink = user?.role === 'admin' ? '/admin/dashboard' : '/dashboard';
	const links = isAuthenticated
		? privateLinks.map((link) => (link.to === '/dashboard' ? { ...link, to: dashboardLink } : link))
		: publicLinks;
	const roleLabel = user?.role === 'admin' ? 'Administrateur' : 'Utilisateur';
	const RoleIcon = user?.role === 'admin' ? ShieldCheck : UserIcon;

	const isHashLinkActive = (href) => {
		const [targetPath = '/', hashPart = ''] = href.split('#');
		const targetHash = hashPart ? `#${hashPart}` : '';
		return location.pathname === targetPath && location.hash === targetHash;
	};

	const handleLogout = async () => {
		await logout();
	};

	return (
		<header className="navbar">
			<div className="navbar-brand">
				<img src={empLogo} alt="EMP" className="navbar-logo" />
				<div>
					<p className="navbar-title">EMP SmartOCR</p>
					<p className="navbar-tagline">Intelligence douanière automatisée</p>
				</div>
			</div>
			<nav className="navbar-links">
				{links.map((link) =>
					link.type === 'hash' ? (
						<Link
							key={link.href}
							to={link.href}
							className={`navbar-link ${isHashLinkActive(link.href) ? 'active' : ''}`}
						>
							{link.label}
						</Link>
					) : (
						<NavLink
							key={link.to}
							to={link.to}
							className={({ isActive }) => {
								const keepHomeInactiveOnHash = link.to === '/' && Boolean(location.hash);
								return `navbar-link ${isActive && !keepHomeInactiveOnHash ? 'active' : ''}`;
							}}
							end={link.to === '/'}
						>
							{link.label}
						</NavLink>
					),
				)}
			</nav>
			<div className="navbar-right">
				{isAuthenticated ? (
					<>
						<span className="role-badge">
							<RoleIcon size={16} /> {roleLabel}
						</span>
						<span className="user-email">{user?.email || 'user@example.com'}</span>
						<NavLink to="/login" className="login-btn" title="Se connecter avec un autre compte">
							Connexion
						</NavLink>
						<button className="logout-btn" onClick={handleLogout}>
							<LogOut size={16} />
							Déconnexion
						</button>
					</>
				) : (
					<NavLink to="/login" className="login-btn">
						Se connecter
					</NavLink>
				)}
			</div>
		</header>
	);
}

export default Navbar;
