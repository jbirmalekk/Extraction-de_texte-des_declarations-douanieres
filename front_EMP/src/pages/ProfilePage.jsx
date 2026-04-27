import { useEffect, useState } from 'react';
import { KeyRound, Save, UserRound } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { changeMyPassword, updateMyProfile } from '../services/userService';
import { validatePasswordPolicy } from '../utils/passwordPolicy';

function ProfilePage() {
	const { user, refreshUser } = useAuth();
	const [username, setUsername] = useState('');
	const [email, setEmail] = useState('');
	const [currentPassword, setCurrentPassword] = useState('');
	const [newPassword, setNewPassword] = useState('');
	const [confirmPassword, setConfirmPassword] = useState('');
	const [profileMessage, setProfileMessage] = useState('');
	const [passwordMessage, setPasswordMessage] = useState('');
	const [profileStatus, setProfileStatus] = useState('neutral');
	const [passwordStatus, setPasswordStatus] = useState('neutral');
	const [profileLoading, setProfileLoading] = useState(false);
	const [passwordLoading, setPasswordLoading] = useState(false);

	useEffect(() => {
		setUsername(user?.username || '');
		setEmail(user?.email || '');
	}, [user]);

	const handleProfileSubmit = async (event) => {
		event.preventDefault();
		setProfileLoading(true);
		setProfileMessage('');
		setProfileStatus('neutral');
		try {
			await updateMyProfile({ username, email });
			await refreshUser();
			setProfileMessage('Profil mis a jour avec succes.');
			setProfileStatus('success');
		} catch (error) {
			setProfileMessage(error?.response?.data?.detail || 'Erreur lors de la mise a jour du profil.');
			setProfileStatus('error');
		} finally {
			setProfileLoading(false);
		}
	};

	const handlePasswordSubmit = async (event) => {
		event.preventDefault();
		setPasswordMessage('');
		setPasswordStatus('neutral');

		const passwordValidation = validatePasswordPolicy(newPassword, 'fr');
		if (!passwordValidation.isValid) {
			setPasswordMessage(passwordValidation.message);
			setPasswordStatus('error');
			return;
		}
		if (newPassword !== confirmPassword) {
			setPasswordMessage('La confirmation du mot de passe est incorrecte.');
			setPasswordStatus('error');
			return;
		}

		setPasswordLoading(true);
		try {
			await changeMyPassword({ currentPassword, newPassword });
			setPasswordMessage('Mot de passe modifie avec succes.');
			setPasswordStatus('success');
			setCurrentPassword('');
			setNewPassword('');
			setConfirmPassword('');
		} catch (error) {
			setPasswordMessage(error?.response?.data?.detail || 'Erreur lors du changement du mot de passe.');
			setPasswordStatus('error');
		} finally {
			setPasswordLoading(false);
		}
	};

	return (
		<div className="profile-page">
			<section className="dashboard-hero modern">
				<div>
					<p className="hero-pill">Mon compte</p>
					<h1>Profil utilisateur</h1>
					<p className="subtitle">Consultez et mettez a jour vos informations personnelles.</p>
				</div>
			</section>

			<div className="profile-grid">
				<section className="profile-card account-card">
					<div className="profile-card-head">
						<span className="profile-card-icon profile-card-icon-account">
							<UserRound size={18} />
						</span>
						<div>
						<h2>Informations du compte</h2>
							<p className="profile-card-subtitle">Mettez a jour vos informations personnelles.</p>
						</div>
					</div>
					<form className="auth-form" onSubmit={handleProfileSubmit}>
						<div className="form-group">
							<label htmlFor="profile-username">Nom utilisateur</label>
							<input
								id="profile-username"
								type="text"
								className="form-input"
								value={username}
								onChange={(event) => setUsername(event.target.value)}
								required
							/>
						</div>
						<div className="form-group">
							<label htmlFor="profile-email">Email</label>
							<input
								id="profile-email"
								type="email"
								className="form-input"
								value={email}
								onChange={(event) => setEmail(event.target.value)}
								required
							/>
						</div>
						{profileMessage && (
							<p className={`profile-message ${profileStatus === 'error' ? 'is-error' : 'is-success'}`}>
								{profileMessage}
							</p>
						)}
						<button type="submit" className="auth-button" disabled={profileLoading}>
							<Save size={16} /> {profileLoading ? 'Mise a jour...' : 'Enregistrer'}
						</button>
					</form>
				</section>

				<section className="profile-card security-card">
					<div className="profile-card-head">
						<span className="profile-card-icon profile-card-icon-security">
							<KeyRound size={18} />
						</span>
						<div>
						<h2>Changer mot de passe</h2>
							<p className="profile-card-subtitle">Renforcez la securite de votre compte.</p>
						</div>
					</div>
					<form className="auth-form" onSubmit={handlePasswordSubmit}>
						<div className="form-group">
							<label htmlFor="current-password">Mot de passe actuel</label>
							<input
								id="current-password"
								type="password"
								className="form-input"
								value={currentPassword}
								onChange={(event) => setCurrentPassword(event.target.value)}
								required
							/>
						</div>
						<div className="form-group">
							<label htmlFor="new-password">Nouveau mot de passe</label>
							<input
								id="new-password"
								type="password"
								className="form-input"
								value={newPassword}
								onChange={(event) => setNewPassword(event.target.value)}
								required
							/>
						</div>
						<div className="form-group">
							<label htmlFor="confirm-new-password">Confirmer le nouveau mot de passe</label>
							<input
								id="confirm-new-password"
								type="password"
								className="form-input"
								value={confirmPassword}
								onChange={(event) => setConfirmPassword(event.target.value)}
								required
							/>
						</div>
						{passwordMessage && (
							<p className={`profile-message ${passwordStatus === 'error' ? 'is-error' : 'is-success'}`}>
								{passwordMessage}
							</p>
						)}
						<button type="submit" className="auth-button" disabled={passwordLoading}>
							<KeyRound size={16} /> {passwordLoading ? 'Modification...' : 'Modifier le mot de passe'}
						</button>
					</form>
				</section>
			</div>
		</div>
	);
}

export default ProfilePage;
