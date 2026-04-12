import { useState } from 'react';
import { Link } from 'react-router-dom';
import empLogo from '../../assets/emp.png';
import { requestPasswordReset } from '../../services/authService';

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
			setMessage(res?.message || 'If the email exists, a reset link has been sent.');
		} catch (err) {
			setError('Unable to send reset link. Please try again.');
		} finally {
			setLoading(false);
		}
	};

	return (
		<div className="auth-container fancy-auth-bg">
			<Link to="/login" className="auth-back">
				<span className="auth-back-arrow">←</span>
				<span>Login</span>
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
						<h2>Password recovery</h2>
						<p>Remember your password?</p>
						<Link to="/login" className="accent-cta">
							Back to login
						</Link>
					</div>
				</div>

				<div className="form-panel fade-up">
					<div className="auth-header split-header">
						<h1>Forgot password</h1>
						<p className="auth-subtitle">Enter your email to receive a reset link.</p>
					</div>

					<form onSubmit={handleSubmit} className="auth-form">
						<div className="form-group">
							<label htmlFor="email">Email</label>
							<input
								id="email"
								type="email"
								className="form-input"
								placeholder="Enter your email"
								value={email}
								onChange={(e) => setEmail(e.target.value)}
								required
							/>
						</div>

						{message && <div className="success-message">{message}</div>}
						{error && <div className="error-message">{error}</div>}

						<button type="submit" className="auth-button" disabled={loading}>
							{loading ? 'Sending...' : 'Send reset link'}
						</button>
					</form>

					<p className="auth-footer">
						Back to{' '}
						<Link to="/login" className="auth-link">
							Sign in
						</Link>
					</p>
				</div>
			</div>
		</div>
	);
}

export default ForgotPasswordPage;
