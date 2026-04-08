import { Link } from 'react-router-dom';

function NotFoundPage() {
	return (
		<div className="auth-container">
			<div className="auth-card">
				<h1>Page not found</h1>
				<p className="auth-subtitle">The page you are looking for does not exist.</p>
				<Link to="/" className="auth-button" style={{ textAlign: 'center' }}>
					Back to home
				</Link>
			</div>
		</div>
	);
}

export default NotFoundPage;
