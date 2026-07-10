import { Link } from 'react-router-dom';

function NotFoundPage() {
	return (
		<div className="auth-container">
			<div className="auth-card">
				<h1>Page introuvable</h1>
				<p className="auth-subtitle">La page que vous recherchez n&apos;existe pas.</p>
				<Link to="/" className="auth-button" style={{ textAlign: 'center' }}>
					Retour à l&apos;accueil
				</Link>
			</div>
		</div>
	);
}

export default NotFoundPage;
