import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import empLogo from '@/assets/emp.png';
import { confirmPasswordReset } from '@/shared/services/authService';
import { validatePasswordPolicy } from '@/shared/utils/passwordPolicy';

function ResetPasswordPage() {
	const [searchParams] = useSearchParams();
	const navigate = useNavigate();
	const [password, setPassword] = useState('');
	const [confirmPassword, setConfirmPassword] = useState('');
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState('');
	const [message, setMessage] = useState('');

	const token = searchParams.get('token') || '';

	const handleSubmit = async (e) => {
		e.preventDefault();
		setError('');
		setMessage('');

		if (!token) {
			setError('Jeton de réinitialisation manquant.');
			return;
		}
		if (password !== confirmPassword) {
			setError('Les mots de passe ne correspondent pas.');
			return;
		}

		const passwordValidation = validatePasswordPolicy(password, 'fr');
		if (!passwordValidation.isValid) {
			setError(passwordValidation.message);
			return;
		}

		setLoading(true);
		try {
			const res = await confirmPasswordReset({ token, newPassword: password });
			setMessage(res?.message || 'Mot de passe réinitialisé avec succès.');
			setTimeout(() => navigate('/login'), 1500);
		} catch (err) {
			setError(err?.response?.data?.detail || 'Échec de la réinitialisation. Réessayez.');
		} finally {
			setLoading(false);
		}
	};

	return (
		<div className="auth-container fancy-auth-bg">
			<Link to="/login" className="auth-back">
				<span className="auth-back-arrow">←</span>
				<span>Connexion</span>
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
						<h2>Nouveau mot de passe</h2>
						<p>Utilisez un mot de passe fort d&apos;au moins 8 caractères.</p>
						<Link to="/login" className="accent-cta">
							Aller à la connexion
						</Link>
					</div>
				</div>

				<div className="form-panel fade-up">
					<div className="auth-header split-header">
						<h1>Réinitialiser le mot de passe</h1>
						<p className="auth-subtitle">Choisissez un nouveau mot de passe.</p>
					</div>

					<form onSubmit={handleSubmit} className="auth-form">
						<div className="form-group">
							<label htmlFor="password">Nouveau mot de passe</label>
							<input
								id="password"
								type="password"
								className="form-input"
								placeholder="Nouveau mot de passe"
								value={password}
								onChange={(e) => setPassword(e.target.value)}
								required
							/>
						</div>

						<div className="form-group">
							<label htmlFor="confirmPassword">Valider le mot de passe</label>
							<input
								id="confirmPassword"
								type="password"
								className="form-input"
								placeholder="Confirmez le mot de passe"
								value={confirmPassword}
								onChange={(e) => setConfirmPassword(e.target.value)}
								required
							/>
						</div>

						{message && <div className="success-message">{message}</div>}
						{error && <div className="error-message">{error}</div>}

						<button type="submit" className="auth-button" disabled={loading}>
							{loading ? 'Réinitialisation…' : 'Réinitialiser'}
						</button>
					</form>

					<p className="auth-footer">
						Retour à la{' '}
						<Link to="/login" className="auth-link">
							connexion
						</Link>
					</p>
				</div>
			</div>
		</div>
	);
}

export default ResetPasswordPage;
