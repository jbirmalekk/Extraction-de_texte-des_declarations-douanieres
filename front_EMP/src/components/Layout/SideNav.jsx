import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
	FileUp,
	History,
	Home,
	LayoutDashboard,
	LogOut,
	Menu,
	ShieldCheck,
	User as UserIcon,
	X,
} from 'lucide-react';
import empLogo from '../../assets/emp.png';
import { useAuth } from '../../hooks/useAuth';

const appLinks = [
	{ to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
	{ to: '/import', label: 'Import', icon: FileUp },
	{ to: '/history', label: 'Historique', icon: History, adminOnly: true },
	{ to: '/admin/users', label: 'Utilisateurs', icon: ShieldCheck, adminOnly: true },
];

function SideNav() {
	const { user, logout } = useAuth();
	const location = useLocation();
	const [mobileOpen, setMobileOpen] = useState(false);
	const visibleLinks = appLinks.filter((link) => !link.adminOnly || user?.role === 'admin');

	useEffect(() => {
		setMobileOpen(false);
	}, [location.pathname]);

	const roleLabel = user?.role === 'admin' ? 'Administrateur' : 'Utilisateur';
	const RoleIcon = user?.role === 'admin' ? ShieldCheck : UserIcon;

	const handleLogout = async () => {
		await logout();
	};

	return (
		<>
			<button
				type="button"
				className="side-nav-toggle"
				onClick={() => setMobileOpen((prev) => !prev)}
				aria-label={mobileOpen ? 'Fermer la navigation' : 'Ouvrir la navigation'}
			>
				{mobileOpen ? <X size={18} /> : <Menu size={18} />}
			</button>

			{mobileOpen && (
				<button
					type="button"
					className="side-nav-overlay"
					onClick={() => setMobileOpen(false)}
					aria-label="Fermer le menu"
				/>
			)}

			<aside className={`side-nav ${mobileOpen ? 'open' : ''}`}>
				<div className="side-brand">
					<img src={empLogo} alt="EMP" className="side-brand-logo" />
					<div className="side-brand-text">
						<p className="side-brand-title">EMP SmartOCR</p>
						<p className="side-brand-tagline">Traitement intelligent</p>
					</div>
				</div>

				<nav className="side-links">
					<NavLink to="/" end className={({ isActive }) => `side-link ${isActive ? 'active' : ''}`}>
						<Home size={18} />
						<span>Accueil</span>
					</NavLink>
					{visibleLinks.map((link) => {
						const Icon = link.icon;
						return (
							<NavLink
								key={link.to}
								to={link.to}
								className={({ isActive }) => `side-link ${isActive ? 'active' : ''}`}
							>
								<Icon size={18} />
								<span>{link.label}</span>
							</NavLink>
						);
					})}
				</nav>

				<div className="side-user-card">
					<span className="side-role-badge">
						<RoleIcon size={15} /> {roleLabel}
					</span>
					<p className="side-user-email">{user?.email || 'user@example.com'}</p>
					<NavLink to="/profile" className={({ isActive }) => `side-profile-btn ${isActive ? 'active' : ''}`}>
						<UserIcon size={16} />
						<span>Mon profil</span>
					</NavLink>
					<button type="button" className="side-logout-btn" onClick={handleLogout}>
						<LogOut size={16} />
						<span>Déconnexion</span>
					</button>
				</div>
			</aside>
		</>
	);
}

export default SideNav;