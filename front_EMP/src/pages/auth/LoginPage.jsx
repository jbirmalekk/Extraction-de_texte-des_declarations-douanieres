import { Link, useLocation, useNavigate } from 'react-router-dom';
import empLogo from '../../assets/emp.png';
import LoginForm from '../../components/Auth/LoginForm';

function LoginPage() {
	const navigate = useNavigate();
	const location = useLocation();
	const from = location.state?.from?.pathname || '/dashboard';
	const successMessage = location.state?.message;

	return (
		<div className="auth-container fancy-auth-bg">
			<Link to="/" className="auth-back">
				<span className="auth-back-arrow">←</span>
				<span>Welcome</span>
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
						<h2>Hello, Welcome!</h2>
						<p>Don't have an account?</p>
						<Link to="/register" className="accent-cta">
							Registre
						</Link>
					</div>
				</div>

				<div className="form-panel fade-up">
					<div className="auth-header split-header">
						<h1>Login</h1>
						<p className="auth-subtitle">Welcome back! Please login to your account.</p>
					</div>

					{successMessage && <div className="success-message">{successMessage}</div>}

					<LoginForm onSuccess={() => navigate(from, { replace: true })} />

					<p className="auth-footer">
						Don't have an account?{' '}
						<Link to="/register" className="auth-link">
							Create account
						</Link>
					</p>
				</div>
			</div>
		</div>
	);
}

export default LoginPage;
