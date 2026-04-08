import { useState } from 'react';
import { Eye, EyeOff, Lock, Mail, ShieldCheck, User } from 'lucide-react';

const roles = [
	{ value: 'user', label: 'User', Icon: User },
	{ value: 'admin', label: 'Administrator', Icon: ShieldCheck },
];

function RegisterForm({ onSuccess }) {
	const [fullName, setFullName] = useState('');
	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [confirmPassword, setConfirmPassword] = useState('');
	const [role, setRole] = useState(roles[0].value);
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
		if (password.length < 6) {
			setPasswordError('Password must be at least 6 characters');
			showToast('error', 'Password must be at least 6 characters');
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
			const storedUsers = JSON.parse(localStorage.getItem('registeredUsers') || '[]');
			const emailExists = storedUsers.some((user) => user.email.toLowerCase() === email.toLowerCase());
			if (emailExists) {
				showToast('error', 'This email is already registered');
				setLoading(false);
				return;
			}

			const newUser = { fullName, email, role, createdAt: new Date().toISOString() };
			localStorage.setItem('registeredUsers', JSON.stringify([...storedUsers, newUser]));
			localStorage.setItem('currentUser', JSON.stringify(newUser));

			showToast('success', 'Account created successfully! Welcome to CustomsOCR Pro.');
			onSuccess?.(newUser);
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

			<div className="form-group">
				<label className="role-hint">Your role in the organization</label>
				<div className="role-toggle">
					{roles.map(({ value, label, Icon }) => (
						<button
							key={value}
							type="button"
							className={`role-option ${role === value ? 'active' : ''}`}
							onClick={() => setRole(value)}
						>
							<span className="role-icon">
								<Icon size={18} />
							</span>
							<span className="role-label">{label}</span>
						</button>
					))}
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
