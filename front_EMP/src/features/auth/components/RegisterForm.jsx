import { useState } from 'react';
import { Eye, EyeOff, Lock, Mail, ShieldCheck } from 'lucide-react';
import { signup } from '../../services/authService';
import { validatePasswordPolicy } from '../../utils/passwordPolicy';

function RegisterForm({ onSuccess }) {
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
			showToast('error', 'Tous les champs sont obligatoires.');
			return false;
		}
		if (password !== confirmPassword) {
			setPasswordError('Les mots de passe ne correspondent pas.');
			showToast('error', 'Les mots de passe ne correspondent pas.');
			return false;
		}

		const passwordValidation = validatePasswordPolicy(password, 'fr');
		if (!passwordValidation.isValid) {
			setPasswordError(passwordValidation.message);
			showToast('error', passwordValidation.message);
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

			const createdUser = await signup({
				fullName: normalizedFullName,
				email: normalizedEmail,
				password,
			});
			showToast(
				'success',
				'Compte créé. Vérifiez votre e-mail et attendez l\'approbation admin avant de vous connecter.',
			);
			onSuccess?.(createdUser);
		} catch (err) {
			const message = err?.response?.data?.detail || 'Impossible de créer le compte.';
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
					<label htmlFor="fullName">Nom complet</label>
					<input
						id="fullName"
						type="text"
						className="form-input"
						placeholder="Votre nom complet"
						value={fullName}
						onChange={(e) => setFullName(e.target.value)}
						required
					/>
				</div>

				<div className="form-group">
					<label htmlFor="email">E-mail</label>
					<div className="input-with-icon">
						<span className="input-icon">
							<Mail size={18} />
						</span>
						<input
							id="email"
							type="email"
							className="form-input password-input"
							placeholder="votre@email.com"
							value={email}
							onChange={(e) => setEmail(e.target.value)}
							required
						/>
					</div>
				</div>
			</div>

			<div className="form-row">
				<div className="form-group">
					<label htmlFor="password">Mot de passe</label>
					<div className="input-with-icon">
						<span className="input-icon">
							<Lock size={18} />
						</span>
						<input
							id="password"
							type={showPassword ? 'text' : 'password'}
							className="form-input password-input"
							placeholder="Créez un mot de passe"
							value={password}
							onChange={(e) => setPassword(e.target.value)}
							required
						/>
						<button
							type="button"
							className="toggle-visibility"
							onClick={() => setShowPassword((prev) => !prev)}
							aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
						>
							{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
						</button>
					</div>
				</div>

				<div className="form-group">
					<label htmlFor="confirmPassword">Valider le mot de passe</label>
					<div className="input-with-icon">
						<span className="input-icon">
							<ShieldCheck size={18} />
						</span>
						<input
							id="confirmPassword"
							type={showConfirmPassword ? 'text' : 'password'}
							className="form-input password-input"
							placeholder="Confirmez votre mot de passe"
							value={confirmPassword}
							onChange={(e) => setConfirmPassword(e.target.value)}
							required
						/>
						<button
							type="button"
							className="toggle-visibility"
							onClick={() => setShowConfirmPassword((prev) => !prev)}
							aria-label={showConfirmPassword ? 'Masquer la confirmation' : 'Afficher la confirmation'}
						>
							{showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
						</button>
					</div>
				</div>
			</div>

			{passwordError && <div className="error-message">{passwordError}</div>}
			{error && <div className="error-message">{error}</div>}

			<button type="submit" className="auth-button" disabled={loading}>
				{loading ? 'Création du compte…' : 'S\'inscrire'}
			</button>
		</form>
		</>
	);
}

export default RegisterForm;
