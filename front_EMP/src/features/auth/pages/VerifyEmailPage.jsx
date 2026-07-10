import { CheckCircle, AlertCircle, Loader } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { verifyEmail } from '../services/userService';

function VerifyEmailPage() {
	const [searchParams] = useSearchParams();
	const navigate = useNavigate();
	const [status, setStatus] = useState('loading'); // loading, success, error
	const [message, setMessage] = useState('');

	useEffect(() => {
		const verifyToken = async () => {
			const token = searchParams.get('token');

			if (!token) {
				setStatus('error');
				setMessage('Token de vérification manquant.');
				return;
			}

			try {
				const result = await verifyEmail(token);
				setStatus('success');
				setMessage(result.message || 'Email vérifié avec succès!');

				// Rediriger vers la page de connexion après 3 secondes
				setTimeout(() => {
					navigate('/login', { replace: true });
				}, 3000);
			} catch (err) {
				setStatus('error');
				setMessage(
					err?.response?.data?.detail ||
					'Erreur lors de la vérification de l\'email. Le lien a peut-être expiré.',
				);
			}
		};

		verifyToken();
	}, [searchParams, navigate]);

	return (
		<div className="verify-email-page">
			<section className="dashboard-hero modern">
				<div>
					<h1>Vérification d'email</h1>
					<p className="subtitle">Vérifions votre adresse email pour accéder à l'application.</p>
				</div>
			</section>

			<section className="activities">
				<div className="verify-email-container">
					{status === 'loading' && (
						<div className="verify-email-card loading">
							<Loader size={48} className="spinner" />
							<h2>Vérification en cours...</h2>
							<p>Veuillez patienter un moment.</p>
						</div>
					)}

					{status === 'success' && (
						<div className="verify-email-card success">
							<CheckCircle size={48} className="success-icon" />
							<h2>Email vérifié!</h2>
							<p>{message}</p>
							<p className="redirect-info">
								Redirection vers la page de connexion...
							</p>
						</div>
					)}

					{status === 'error' && (
						<div className="verify-email-card error">
							<AlertCircle size={48} className="error-icon" />
							<h2>Erreur de vérification</h2>
							<p>{message}</p>
							<div className="verify-email-actions">
								<button
									className="btn-primary"
									onClick={() => navigate('/login', { replace: true })}
								>
									Retour à la connexion
								</button>
								<button
									className="btn-secondary"
									onClick={() => navigate('/register', { replace: true })}
								>
									Nouvelle inscription
								</button>
							</div>
						</div>
					)}
				</div>
			</section>
		</div>
	);
}

export default VerifyEmailPage;
