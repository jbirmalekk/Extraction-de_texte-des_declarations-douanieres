import { useEffect, useMemo, useState } from 'react';
import {
	Camera,
	Info,
	RotateCcw,
	Save,
	Shield,
	UserRound,
} from 'lucide-react';
import { useAuth } from '@/shared/hooks/useAuth';
import { fetchMyDashboard } from '@/shared/services/ocrService';
import { changeMyPassword, updateMyProfile } from '@/shared/services/userService';
import { validatePasswordPolicy } from '@/shared/utils/passwordPolicy';

const DEPARTMENT_OPTIONS = [
	{ value: 'logistics', label: 'Logistique & Opérations' },
	{ value: 'customs', label: 'Douane & Conformité' },
	{ value: 'finance', label: 'Finance & Comptabilité' },
	{ value: 'admin', label: 'Administration' },
];

const MONTHLY_QUOTA = 100;

function ProfilePage() {
	const { user, refreshUser } = useAuth();
	const [username, setUsername] = useState('');
	const [email, setEmail] = useState('');
	const [department, setDepartment] = useState('logistics');
	const [currentPassword, setCurrentPassword] = useState('');
	const [newPassword, setNewPassword] = useState('');
	const [confirmPassword, setConfirmPassword] = useState('');
	const [profileMessage, setProfileMessage] = useState('');
	const [passwordMessage, setPasswordMessage] = useState('');
	const [profileStatus, setProfileStatus] = useState('neutral');
	const [passwordStatus, setPasswordStatus] = useState('neutral');
	const [profileLoading, setProfileLoading] = useState(false);
	const [passwordLoading, setPasswordLoading] = useState(false);
	const [metricsLoading, setMetricsLoading] = useState(true);
	const [docsScanned, setDocsScanned] = useState(0);

	const initialProfile = useMemo(
		() => ({
			username: user?.username || '',
			email: user?.email || '',
			department: user?.role === 'admin' ? 'admin' : 'logistics',
		}),
		[user],
	);

	const hasProfileChanges =
		username !== initialProfile.username ||
		email !== initialProfile.email ||
		department !== initialProfile.department;

	useEffect(() => {
		setUsername(initialProfile.username);
		setEmail(initialProfile.email);
		setDepartment(initialProfile.department);
	}, [initialProfile]);

	useEffect(() => {
		let active = true;

		const loadMetrics = async () => {
			setMetricsLoading(true);
			try {
				const data = await fetchMyDashboard();
				if (active) {
					setDocsScanned(Number(data?.stats?.documents_processed || 0));
				}
			} catch (_error) {
				if (active) {
					setDocsScanned(0);
				}
			} finally {
				if (active) {
					setMetricsLoading(false);
				}
			}
		};

		loadMetrics();
		return () => {
			active = false;
		};
	}, []);

	const quotaPercent = Math.min(100, Math.round((docsScanned / MONTHLY_QUOTA) * 100));

	const handleDiscard = () => {
		setUsername(initialProfile.username);
		setEmail(initialProfile.email);
		setDepartment(initialProfile.department);
		setProfileMessage('');
		setProfileStatus('neutral');
	};

	const handleProfileSubmit = async (event) => {
		event.preventDefault();
		setProfileLoading(true);
		setProfileMessage('');
		setProfileStatus('neutral');
		try {
			await updateMyProfile({ username, email });
			await refreshUser();
			setProfileMessage('Profil mis à jour avec succès.');
			setProfileStatus('success');
		} catch (error) {
			setProfileMessage(error?.response?.data?.detail || 'Erreur lors de la mise à jour du profil.');
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
			setPasswordMessage('Mot de passe modifié avec succès.');
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

	const roleLabel = user?.role === 'admin' ? 'Administrateur' : 'Utilisateur';
	const employeeId = user?.id ? `EMP-${String(user.id).padStart(5, '0')}` : '—';
	const avatarInitials = (username || user?.email || 'U')
		.split(/[\s@._-]+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((part) => part[0]?.toUpperCase())
		.join('');

	return (
		<div className="profile-settings-page">
			<header className="profile-settings-header">
				<div>
					<h1>Paramètres du profil</h1>
					<p className="profile-settings-subtitle">
						Gérez vos informations personnelles et vos préférences de sécurité.
					</p>
				</div>
				<div className="profile-settings-actions">
					<button
						type="button"
						className="profile-btn profile-btn-outline"
						onClick={handleDiscard}
						disabled={!hasProfileChanges || profileLoading}
					>
						Annuler
					</button>
					<button
						type="submit"
						form="profile-form"
						className="profile-btn profile-btn-primary"
						disabled={profileLoading || !hasProfileChanges}
					>
						<Save size={16} />
						{profileLoading ? 'Enregistrement…' : 'Enregistrer'}
					</button>
				</div>
			</header>

			<div className="profile-settings-layout">
				<div className="profile-settings-main">
					<section className="profile-settings-card">
						<div className="profile-settings-card-head">
							<span className="profile-settings-card-icon">
								<UserRound size={18} />
							</span>
							<h2>Informations personnelles</h2>
						</div>

						<form id="profile-form" className="profile-settings-form" onSubmit={handleProfileSubmit}>
							<div className="profile-form-grid">
								<div className="form-group">
									<label htmlFor="profile-fullname">Nom complet</label>
									<input
										id="profile-fullname"
										type="text"
										className="form-input"
										value={username}
										onChange={(event) => setUsername(event.target.value)}
										required
									/>
								</div>
								<div className="form-group">
									<label htmlFor="profile-email">Adresse e-mail</label>
									<input
										id="profile-email"
										type="email"
										className="form-input"
										value={email}
										onChange={(event) => setEmail(event.target.value)}
										required
									/>
								</div>
								<div className="form-group">
									<label htmlFor="profile-employee-id">Identifiant employé</label>
									<input
										id="profile-employee-id"
										type="text"
										className="form-input profile-input-readonly"
										value={employeeId}
										readOnly
									/>
								</div>
								<div className="form-group">
									<label htmlFor="profile-department">Département</label>
									<select
										id="profile-department"
										className="form-input profile-select"
										value={department}
										onChange={(event) => setDepartment(event.target.value)}
									>
										{DEPARTMENT_OPTIONS.map((option) => (
											<option key={option.value} value={option.value}>
												{option.label}
											</option>
										))}
									</select>
								</div>
							</div>

							<div className="profile-info-banner">
								<Info size={18} />
								<p>
									La modification de votre e-mail principal nécessitera un nouveau lien de
									vérification. Votre accès à EMP SmartOCR sera temporairement restreint jusqu&apos;à
									confirmation.
								</p>
							</div>

							{profileMessage ? (
								<p className={`profile-message ${profileStatus === 'error' ? 'is-error' : 'is-success'}`}>
									{profileMessage}
								</p>
							) : null}
						</form>
					</section>

					<section className="profile-settings-card profile-security-card">
						<div className="profile-settings-card-head">
							<span className="profile-settings-card-icon profile-settings-card-icon-security">
								<RotateCcw size={18} />
							</span>
							<h2>Sécurité et authentification</h2>
						</div>

						<div className="profile-security-grid">
							<div className="profile-security-copy">
								<h3>Mise à jour du mot de passe</h3>
								<p>
									Nous recommandons un mot de passe fort et unique, que vous n&apos;utilisez pas
									ailleurs.
								</p>
							</div>

							<form className="profile-password-form" onSubmit={handlePasswordSubmit}>
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
									<label htmlFor="confirm-new-password">Valider le mot de passe</label>
									<input
										id="confirm-new-password"
										type="password"
										className="form-input"
										value={confirmPassword}
										onChange={(event) => setConfirmPassword(event.target.value)}
										required
									/>
								</div>

								{passwordMessage ? (
									<p className={`profile-message ${passwordStatus === 'error' ? 'is-error' : 'is-success'}`}>
										{passwordMessage}
									</p>
								) : null}

								<button type="submit" className="profile-btn profile-btn-primary profile-btn-block" disabled={passwordLoading}>
									{passwordLoading ? 'Modification…' : 'Modifier le mot de passe'}
								</button>
							</form>
						</div>

						
					</section>
				</div>

				<aside className="profile-settings-aside">
					<section className="profile-settings-card profile-avatar-card">
						<div className="profile-avatar-wrap">
							<div className="profile-avatar-circle" aria-hidden="true">
								{avatarInitials}
							</div>
							<button type="button" className="profile-avatar-camera" aria-label="Changer la photo" disabled>
								<Camera size={14} />
							</button>
						</div>
						<h3>{username || 'Utilisateur'}</h3>
						<p className="profile-avatar-email">{email || '—'}</p>
						<p className="profile-avatar-role">{roleLabel}</p>
						<button type="button" className="profile-btn profile-btn-outline profile-btn-block" disabled>
							Changer la photo
						</button>
					</section>

					<section className="profile-settings-card profile-metrics-card">
						<h2>Métriques du compte</h2>
						<div className="profile-metric-row">
							<span>Traitement OCR</span>
							<strong className="profile-metric-active">ACTIF</strong>
						</div>
						<div className="profile-metric-row">
							<span>Documents scannés</span>
							<strong>{metricsLoading ? '…' : docsScanned.toLocaleString('fr-FR')}</strong>
						</div>
						<div className="profile-quota">
							<div className="profile-quota-labels">
								<span>Quota mensuel</span>
								<span>{metricsLoading ? '…' : `${quotaPercent} %`}</span>
							</div>
							<div className="profile-quota-track" aria-hidden="true">
								<span
									className="profile-quota-fill"
									style={{ width: `${metricsLoading ? 0 : quotaPercent}%` }}
								/>
							</div>
						</div>
					</section>
				</aside>
			</div>
		</div>
	);
}

export default ProfilePage;

