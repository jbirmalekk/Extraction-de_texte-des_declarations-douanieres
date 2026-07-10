import { Link, useNavigate } from 'react-router-dom';
import empLogo from '../../assets/emp.png';
import RegisterForm from '../../components/Auth/RegisterForm';

function RegisterPage() {
	const navigate = useNavigate();

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
						<h2>Bon retour !</h2>
						<p>Vous avez déjà un compte ?</p>
						<Link to="/login" className="accent-cta">
							Connexion
						</Link>
					</div>
				</div>

				<div className="form-panel fade-up">
					<div className="auth-header split-header">
						
						<h1>Créer un compte</h1>
						<p className="auth-subtitle">Automatisez le traitement de vos documents douaniers</p>
					</div>

					<RegisterForm
						onSuccess={() =>
							navigate('/login', {
								replace: true,
								state: {
									message:
										'Compte créé. Vérifiez votre e-mail et attendez l\'approbation d\'un administrateur.',
								},
							})
						}
					/>

					<p className="auth-footer">
						Vous avez déjà un compte ?{' '}
						<Link to="/login" className="auth-link">
							Se connecter
						</Link>
					</p>
				</div>
			</div>
		</div>
	);
}

export default RegisterPage;
