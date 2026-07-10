import { Link, useLocation, useNavigate } from 'react-router-dom';
import empLogo from '../../assets/emp.png';
import LoginForm from '../../components/Auth/LoginForm';

function LoginPage() {
	const navigate = useNavigate();
	const location = useLocation();
	const from = location.state?.from?.pathname || '/dashboard';
	const successMessage = location.state?.message;

	const handleLoginSuccess = (authData) => {
		const roleAwareDestination = authData?.user?.role === 'admin' ? '/admin/dashboard' : from;
		navigate(roleAwareDestination, { replace: true });
	};

	return (
		<div className="auth-container fancy-auth-bg">
			<Link to="/" className="auth-back">
				<span className="auth-back-arrow">←</span>
				<span>Accueil</span>
			</Link>
			<div className="auth-blob auth-blob-one" />
			<div className="auth-blob auth-blob-two" />
			<div className="auth-split">
				<div className="accent-panel">
					<div className="accent-content">
						<div className="accent-brand">
							<img src={empLogo} alt="EMP Logo" className="accent-logo" />
							<span className="accent-name">EMP SmartOCR</span>
						</div>
						<h2>Bonjour, bienvenue !</h2>
						<p>Vous n&apos;avez pas de compte ?</p>
						<Link to="/register" className="accent-cta">
							S&apos;inscrire
						</Link>
					</div>
				</div>

				<div className="form-panel fade-up">
					<div className="auth-header split-header">
						<h1>Connexion</h1>
						<p className="auth-subtitle">Bon retour ! Connectez-vous à votre compte.</p>
					</div>

					{successMessage && <div className="success-message">{successMessage}</div>}

					<LoginForm onSuccess={handleLoginSuccess} />

					<p className="auth-footer">
						Vous n&apos;avez pas de compte ?{' '}
						<Link to="/register" className="auth-link">
							Créer un compte
						</Link>
					</p>
				</div>
			</div>
		</div>
	);
}

export default LoginPage;
