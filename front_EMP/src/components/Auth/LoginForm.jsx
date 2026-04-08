import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye, EyeOff, Lock, Mail } from 'lucide-react';
import { healthCheck } from '../../services/api';
import { useAuth } from '../../hooks/useAuth';

function LoginForm({ onSuccess }) {
	const { login } = useAuth();
	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [showPassword, setShowPassword] = useState(false);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState('');
	const [dbStatus, setDbStatus] = useState('');
	const [dbChecking, setDbChecking] = useState(false);
	const [dbError, setDbError] = useState('');

	const handleSubmit = async (event) => {
		event.preventDefault();
		setLoading(true);
		setError('');
		try {
			await login({ email, password });
			onSuccess?.();
		} catch (err) {
			const message = err?.response?.data?.detail || 'Invalid email or password';
			setError(message);
		} finally {
			setLoading(false);
		}
	};

	const handleDbConnect = async () => {
		setDbChecking(true);
		setDbStatus('');
		setDbError('');

		try {
			const data = await healthCheck();
			if (data?.status === 'healthy') {
				setDbStatus('✅ Connected to database successfully');
				setTimeout(() => setDbStatus(''), 5000);
			} else {
				setDbError('⚠️ Database connection failed');
			}
		} catch (err) {
			setDbError('❌ Connection failed. Please verify backend is running.');
		} finally {
			setDbChecking(false);
		}
	};

	return (
		<>
			<form onSubmit={handleSubmit} className="auth-form">
				<div className="form-group" >
					<label htmlFor="email">Email</label>
					<div className="input-with-icon">
						<span className="input-icon">
							<Mail size={18} />
						</span>
						<input
							id="email"
							type="email"
							className="form-input password-input"
							placeholder="your@email.com"
							value={email}
							onChange={(e) => setEmail(e.target.value)}
							required
						/>
					</div>
				</div>

				<div className="form-group">
					<div className="password-header">
						<label htmlFor="password">Password</label>
						<Link to="/forgot-password" className="forgot-link">
							Forgot password?
						</Link>
					</div>
					<div className="input-with-icon">
						<span className="input-icon">
							<Lock size={18} />
						</span>
						<input
							id="password"
							type={showPassword ? 'text' : 'password'}
							className="form-input password-input"
							placeholder="Enter your password"
							value={password}
							onChange={(e) => setPassword(e.target.value)}
							required
						/>
						<button
							type="button"
							className="toggle-visibility"
							onClick={() => setShowPassword((prev) => !prev)}
							aria-label={showPassword ? 'Hide password' : 'Show password'}
						>
							{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
						</button>
					</div>
				</div>

				{error && <div className="error-message">{error}</div>}

				<button type="submit" className="auth-button" disabled={loading}>
					{loading ? 'Signing in...' : 'Sign in'}
				</button>
			</form>

			<div className="db-connection-section">
				<button
					type="button"
					className="db-connect-button"
					onClick={handleDbConnect}
					disabled={dbChecking}
				>
					<span className="db-icon">🔌</span>
					{dbChecking ? 'Connecting...' : 'Connect to database'}
				</button>

				{dbStatus && <div className="db-status success">{dbStatus}</div>}
				{dbError && <div className="db-status error">{dbError}</div>}
			</div>
		</>
	);
}

export default LoginForm;
