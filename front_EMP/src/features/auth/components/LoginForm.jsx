import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye, EyeOff, Lock, Mail } from 'lucide-react';
import { healthCheck } from '@/shared/services/api';
import { useAuth } from '@/shared/hooks/useAuth';

function LoginForm({ onSuccess }) {
	const { login } = useAuth();
	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [showPassword, setShowPassword] = useState(false);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState('');
	const [dbStatus, setDbStatus] = useState('');
	const [dbChecking, setDbChecking] = useState(false);
	const [dbError, setDbError] = useState('');

	const handleSubmit = async (event) => {
		event.preventDefault();
		setLoading(true);
		setError('');
		try {
			const authData = await login({ email, password });
			onSuccess?.(authData);
		} catch (err) {
			const message = err?.response?.data?.detail || 'E-mail ou mot de passe incorrect.';
			setError(message);
		} finally {
			setLoading(false);
		}
	};

	const handleDbConnect = async () => {
		setDbChecking(true);
		setDbStatus('');
		setDbError('');

		try {
			const data = await healthCheck();
			if (data?.status === 'healthy') {
				setDbStatus('Connexion à la base de données réussie.');
				setTimeout(() => setDbStatus(''), 5000);
			} else {
				setDbError('Échec de la connexion à la base de données.');
			}
		} catch (err) {
			setDbError('Connexion impossible. Vérifiez que le backend est démarré.');
		} finally {
			setDbChecking(false);
		}
	};

	return (
		<>
			<form onSubmit={handleSubmit} className="auth-form">
				<div className="form-group">
					<label htmlFor="email">E-mail</label>
					<div className="input-with-icon">
						<span className="input-icon">
							<Mail size={18} />
						</span>
						<input
							id="email"
							type="email"
							className="form-input password-input"
							placeholder="votre@email.com"
							value={email}
							onChange={(e) => setEmail(e.target.value)}
							required
						/>
					</div>
				</div>

				<div className="form-group">
					<div className="password-header">
						<label htmlFor="password">Mot de passe</label>
						<Link to="/forgot-password" className="forgot-link">
							Mot de passe oublié ?
						</Link>
					</div>
					<div className="input-with-icon">
						<span className="input-icon">
							<Lock size={18} />
						</span>
						<input
							id="password"
							type={showPassword ? 'text' : 'password'}
							className="form-input password-input"
							placeholder="Saisissez votre mot de passe"
							value={password}
							onChange={(e) => setPassword(e.target.value)}
							required
						/>
						<button
							type="button"
							className="toggle-visibility"
							onClick={() => setShowPassword((prev) => !prev)}
							aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
						>
							{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
						</button>
					</div>
				</div>

				{error && <div className="error-message">{error}</div>}

				<button type="submit" className="auth-button" disabled={loading}>
					{loading ? 'Connexion…' : 'Se connecter'}
				</button>
			</form>

			<div className="db-connection-section">
				<button
					type="button"
					className="db-connect-button"
					onClick={handleDbConnect}
					disabled={dbChecking}
				>
					<span className="db-icon">🔌</span>
					{dbChecking ? 'Connexion…' : 'Tester la connexion base de données'}
				</button>

				{dbStatus && <div className="db-status success">{dbStatus}</div>}
				{dbError && <div className="db-status error">{dbError}</div>}
			</div>
		</>
	);
}

export default LoginForm;

