import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import empLogo from '../../assets/emp.png';
import { confirmPasswordReset } from '../../services/authService';

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
			setError('Reset token is missing.');
			return;
		}
		if (password !== confirmPassword) {
			setError('Passwords do not match');
			return;
		}
		if (password.length < 8) {
			setError('Password must be at least 8 characters');
			return;
		}

		setLoading(true);
		try {
			const res = await confirmPasswordReset({ token, newPassword: password });
			setMessage(res?.message || 'Password reset successful');
			setTimeout(() => navigate('/login'), 1500);
		} catch (err) {
			setError(err?.response?.data?.detail || 'Reset failed. Try again.');
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
						<h2>Create a new password</h2>
						<p>Use a strong password with at least 8 characters.</p>
						<Link to="/login" className="accent-cta">
							Go to login
						</Link>
					</div>
				</div>

				<div className="form-panel fade-up">
					<div className="auth-header split-header">
						<h1>Reset password</h1>
						<p className="auth-subtitle">Choose a new password.</p>
					</div>

					<form onSubmit={handleSubmit} className="auth-form">
						<div className="form-group">
							<label htmlFor="password">New password</label>
							<input
								id="password"
								type="password"
								className="form-input"
								placeholder="Enter new password"
								value={password}
								onChange={(e) => setPassword(e.target.value)}
								required
							/>
						</div>

						<div className="form-group">
							<label htmlFor="confirmPassword">Confirm password</label>
							<input
								id="confirmPassword"
								type="password"
								className="form-input"
								placeholder="Confirm new password"
								value={confirmPassword}
								onChange={(e) => setConfirmPassword(e.target.value)}
								required
							/>
						</div>

						{message && <div className="success-message">{message}</div>}
						{error && <div className="error-message">{error}</div>}

						<button type="submit" className="auth-button" disabled={loading}>
							{loading ? 'Resetting...' : 'Reset password'}
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

export default ResetPasswordPage;
