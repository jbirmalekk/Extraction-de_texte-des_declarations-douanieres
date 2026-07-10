import { useState } from 'react';
import { Link } from 'react-router-dom';
import empLogo from '@/assets/emp.png';
import { requestPasswordReset } from '@/shared/services/authService';

function ForgotPasswordPage() {
	const [email, setEmail] = useState('');
	const [loading, setLoading] = useState(false);
	const [message, setMessage] = useState('');
	const [error, setError] = useState('');

	const handleSubmit = async (e) => {
		e.preventDefault();
		setLoading(true);
		setMessage('');
		setError('');
		try {
			const res = await requestPasswordReset(email);
			setMessage(res?.message || 'Si cet e-mail existe, un lien de réinitialisation a été envoyé.');
		} catch (err) {
			setError(err?.response?.data?.detail || 'Impossible d\'envoyer le lien. Réessayez.');
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
						<h2>Récupération du mot de passe</h2>
						<p>Vous vous souvenez de votre mot de passe ?</p>
						<Link to="/login" className="accent-cta">
							Retour à la connexion
						</Link>
					</div>
				</div>

				<div className="form-panel fade-up">
					<div className="auth-header split-header">
						<h1>Mot de passe oublié</h1>
						<p className="auth-subtitle">Saisissez votre e-mail pour recevoir un lien de réinitialisation.</p>
					</div>

					<form onSubmit={handleSubmit} className="auth-form">
						<div className="form-group">
							<label htmlFor="email">E-mail</label>
							<input
								id="email"
								type="email"
								className="form-input"
								placeholder="votre@email.com"
								value={email}
								onChange={(e) => setEmail(e.target.value)}
								required
							/>
						</div>

						{message && <div className="success-message">{message}</div>}
						{error && <div className="error-message">{error}</div>}

						<button type="submit" className="auth-button" disabled={loading}>
							{loading ? 'Envoi…' : 'Envoyer le lien'}
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

export default ForgotPasswordPage;
