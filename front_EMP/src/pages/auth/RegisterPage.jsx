import { Link, useNavigate } from 'react-router-dom';
import empLogo from '../../assets/emp.png';
import RegisterForm from '../../components/Auth/RegisterForm';

function RegisterPage() {
	const navigate = useNavigate();

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
						<h2>Welcome Back!</h2>
						<p>Already have an account?</p>
						<Link to="/login" className="accent-cta">
							Login
						</Link>
					</div>
				</div>

				<div className="form-panel fade-up">
					<div className="auth-header split-header">
						
						<h1>Create account</h1>
						<p className="auth-subtitle">Join us to start automating your customs documents</p>
					</div>

					<RegisterForm onSuccess={() => navigate('/dashboard')} />

					<p className="auth-footer">
						Already have an account?{' '}
						<Link to="/login" className="auth-link">
							Sign in
						</Link>
					</p>
				</div>
			</div>
		</div>
	);
}

export default RegisterPage;
