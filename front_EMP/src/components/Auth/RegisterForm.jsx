import { useState } from 'react';
import { Eye, EyeOff, Lock, Mail, ShieldCheck } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { signup } from '../../services/authService';

function RegisterForm({ onSuccess }) {
	const { login } = useAuth();
	const [fullName, setFullName] = useState('');
	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [confirmPassword, setConfirmPassword] = useState('');
	const [showPassword, setShowPassword] = useState(false);
	const [showConfirmPassword, setShowConfirmPassword] = useState(false);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState('');
	const [passwordError, setPasswordError] = useState('');
	const [toast, setToast] = useState(null);

	const showToast = (type, message) => {
		setToast({ type, message });
		setTimeout(() => setToast(null), 2800);
	};

	const validatePasswords = () => {
		if (!fullName || !email || !password || !confirmPassword) {
			showToast('error', 'All fields are required');
			return false;
		}
		if (password !== confirmPassword) {
			setPasswordError('Passwords do not match');
			showToast('error', 'Passwords do not match');
			return false;
		}
		if (password.length < 8) {
			setPasswordError('Password must be at least 8 characters');
			showToast('error', 'Password must be at least 8 characters');
			return false;
		}
		setPasswordError('');
		return true;
	};

	const handleSubmit = async (event) => {
		event.preventDefault();

		if (!validatePasswords()) {
			return;
		}

		setLoading(true);
		setError('');

		try {
			const normalizedFullName = fullName.trim();
			const normalizedEmail = email.trim().toLowerCase();

			await signup({
				fullName: normalizedFullName,
				email: normalizedEmail,
				password,
			});

			await login({ email: normalizedEmail, password });

			showToast('success', 'Account created successfully!');
			onSuccess?.();
		} catch (err) {
			const message = err?.response?.data?.detail || 'Unable to create account';
			setError(message);
			showToast('error', message);
		} finally {
			setLoading(false);
		}
	};

	return (
		<>
			{toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}
			<form onSubmit={handleSubmit} className="auth-form">
			<div className="form-row">
				<div className="form-group">
					<label htmlFor="fullName">Full name</label>
					<input
						id="fullName"
						type="text"
						className="form-input"
						placeholder="Your full name"
						value={fullName}
						onChange={(e) => setFullName(e.target.value)}
						required
					/>
				</div>

				<div className="form-group">
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
			</div>

			<div className="form-row">
				<div className="form-group">
					<label htmlFor="password">Password</label>
					<div className="input-with-icon">
						<span className="input-icon">
							<Lock size={18} />
						</span>
						<input
							id="password"
							type={showPassword ? 'text' : 'password'}
							className="form-input password-input"
							placeholder="Create a password"
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

				<div className="form-group">
					<label htmlFor="confirmPassword">Confirm password</label>
					<div className="input-with-icon">
						<span className="input-icon">
							<ShieldCheck size={18} />
						</span>
						<input
							id="confirmPassword"
							type={showConfirmPassword ? 'text' : 'password'}
							className="form-input password-input"
							placeholder="Confirm your password"
							value={confirmPassword}
							onChange={(e) => setConfirmPassword(e.target.value)}
							required
						/>
						<button
							type="button"
							className="toggle-visibility"
							onClick={() => setShowConfirmPassword((prev) => !prev)}
							aria-label={showConfirmPassword ? 'Hide confirmation' : 'Show confirmation'}
						>
							{showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
						</button>
					</div>
				</div>
			</div>

			{passwordError && <div className="error-message">{passwordError}</div>}
			{error && <div className="error-message">{error}</div>}

			<button type="submit" className="auth-button" disabled={loading}>
				{loading ? 'Creating account...' : 'Sign up'}
			</button>
		</form>
		</>
	);
}

export default RegisterForm;
