import { useEffect, useMemo, useState } from 'react';
import { Eye, PencilLine, Trash2, UserRound, Check, X, Clock, Users } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import {
	deleteUserByAdmin,
	getUserByAdmin,
	listUsers,
	updateUserByAdmin,
	getPendingUsers,
	approveUser,
	rejectUser,
} from '../services/userService';

function AdminUsersPage() {
	const { user: currentUser } = useAuth();
	const [users, setUsers] = useState([]);
	const [pendingUsers, setPendingUsers] = useState([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState('');
	const [savingId, setSavingId] = useState(null);
	const [viewUser, setViewUser] = useState(null);
	const [editUserId, setEditUserId] = useState(null);
	const [activeTab, setActiveTab] = useState('pending'); // pending or all
	const [editForm, setEditForm] = useState({ username: '', email: '', role: 'user' });
	const [successMessage, setSuccessMessage] = useState('');

	const loadUsers = async () => {
		setLoading(true);
		setError('');
		try {
			const [allUsers, pending] = await Promise.all([listUsers(), getPendingUsers()]);
			setUsers(Array.isArray(allUsers) ? allUsers : []);
			setPendingUsers(Array.isArray(pending) ? pending : []);
		} catch (err) {
			setError(err?.response?.data?.detail || 'Impossible de charger les utilisateurs.');
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		loadUsers();
	}, []);

	const sortedUsers = useMemo(
		() => [...users].sort((a, b) => (a.id > b.id ? 1 : -1)),
		[users],
	);

	const sortedPendingUsers = useMemo(
		() => [...pendingUsers].sort((a, b) => (a.id > b.id ? 1 : -1)),
		[pendingUsers],
	);

	const openView = async (userId) => {
		setSavingId(userId);
		setError('');
		try {
			const data = await getUserByAdmin(userId);
			setViewUser(data);
		} catch (err) {
			setError(err?.response?.data?.detail || 'Chargement detail utilisateur impossible.');
		} finally {
			setSavingId(null);
		}
	};

	const openEdit = (user) => {
		setError('');
		setSuccessMessage('');
		setEditUserId(user.id);
		setEditForm({
			username: user.username || '',
			email: user.email || '',
			role: user.role || 'user',
		});
	};

	const closeEdit = () => {
		setEditUserId(null);
		setEditForm({ username: '', email: '', role: 'user' });
	};

	const onEditSubmit = async (event) => {
		event.preventDefault();
		if (!editUserId) {
			return;
		}

		const payload = {
			username: editForm.username.trim(),
			email: editForm.email.trim().toLowerCase(),
			role: editForm.role,
		};

		if (payload.username.length < 3) {
			setError('Le nom utilisateur doit contenir au moins 3 caracteres.');
			return;
		}

		setSavingId(editUserId);
		setError('');
		setSuccessMessage('');
		try {
			const updated = await updateUserByAdmin(editUserId, payload);
			setUsers((prev) => prev.map((user) => (user.id === editUserId ? updated : user)));
			setSuccessMessage('Utilisateur mis a jour avec succes.');
			closeEdit();
		} catch (err) {
			setError(err?.response?.data?.detail || 'Mise a jour utilisateur impossible.');
		} finally {
			setSavingId(null);
		}
	};

	const onDelete = async (userId) => {
		const confirmed = window.confirm('Supprimer cet utilisateur ?');
		if (!confirmed) {
			return;
		}

		setSavingId(userId);
		setError('');
		setSuccessMessage('');
		try {
			await deleteUserByAdmin(userId);
			setUsers((prev) => prev.filter((user) => user.id !== userId));
			if (viewUser?.id === userId) {
				setViewUser(null);
			}
			setSuccessMessage('Utilisateur supprime avec succes.');
		} catch (err) {
			setError(err?.response?.data?.detail || 'Suppression impossible.');
		} finally {
			setSavingId(null);
		}
	};

	const onApprove = async (userId) => {
		const confirmed = window.confirm('Approuver ce compte utilisateur ?');
		if (!confirmed) {
			return;
		}

		setSavingId(userId);
		setError('');
		setSuccessMessage('');
		try {
			await approveUser(userId);
			setPendingUsers((prev) => prev.filter((user) => user.id !== userId));
			const approvedUser = pendingUsers.find((u) => u.id === userId);
			setUsers((prev) => {
				const exists = prev.some((user) => user.id === userId);

				if (exists) {
					return prev.map((user) =>
						user.id === userId ? { ...user, is_approved: true, is_active: true } : user,
					);
				}

				if (approvedUser) {
					return [...prev, { ...approvedUser, is_approved: true, is_active: true }];
				}

				return prev;
			});
			setSuccessMessage('Utilisateur approuve avec succes.');
		} catch (err) {
			setError(err?.response?.data?.detail || 'Approbation impossible.');
		} finally {
			setSavingId(null);
		}
	};

	const onReject = async (userId) => {
		const confirmed = window.confirm('Rejeter ce compte utilisateur ? (Cela supprimera le compte)');
		if (!confirmed) {
			return;
		}

		setSavingId(userId);
		setError('');
		setSuccessMessage('');
		try {
			await rejectUser(userId);
			setPendingUsers((prev) => prev.filter((user) => user.id !== userId));
			setUsers((prev) => prev.filter((user) => user.id !== userId));
			if (viewUser?.id === userId) {
				setViewUser(null);
			}
			setSuccessMessage('Utilisateur rejete et supprime.');
		} catch (err) {
			setError(err?.response?.data?.detail || 'Rejet impossible.');
		} finally {
			setSavingId(null);
		}
	};

	return (
		<div className="admin-users-page">
			<section className="dashboard-hero modern">
				<div>
					<p className="hero-pill">Administration</p>
					<h1>Gestion des utilisateurs</h1>
					<p className="subtitle">
						Approuvez les comptes en attente, consultez les details et gerez les roles.
					</p>
				</div>
			</section>

			<section className="activities">
				{successMessage && <p className="profile-message is-success">{successMessage}</p>}

				<div className="admin-tabs">
					<button
						className={`admin-tab ${activeTab === 'pending' ? 'active' : ''}`}
						onClick={() => setActiveTab('pending')}
					>
						<Clock size={18} />
						<span>En attente d'approbation</span>
						<span className="admin-tab-badge pending">{pendingUsers.length}</span>
					</button>
					<button
						className={`admin-tab ${activeTab === 'all' ? 'active' : ''}`}
						onClick={() => setActiveTab('all')}
					>
						<Users size={18} />
						<span>Tous les utilisateurs</span>
						<span className="admin-tab-badge all">{users.length}</span>
					</button>
				</div>

				{loading ? (
					<p>Chargement des utilisateurs...</p>
				) : error ? (
					<p className="error-message">{error}</p>
				) : activeTab === 'pending' ? (
					<div className="admin-users-table">
						{pendingUsers.length === 0 ? (
							<p className="empty-message">Aucun utilisateur en attente d'approbation.</p>
						) : (
							<>
								<div className="admin-users-head">
									<span>Utilisateur</span>
									<span>Email</span>
									<span>Date inscription</span>
									<span>Actions</span>
								</div>
								{sortedPendingUsers.map((user) => (
									<div key={user.id} className="admin-users-row">
										<span className="admin-user-name">
											<UserRound size={15} /> {user.username}
										</span>
										<span>{user.email || '-'}</span>
										<span>
											{user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
										</span>
										<span className="admin-actions">
											<button
												type="button"
												className="table-action success"
												onClick={() => onApprove(user.id)}
												disabled={savingId === user.id}
												title="Approuver ce compte"
											>
												<Check size={14} /> Approuver
											</button>
											<button
												type="button"
												className="table-action danger"
												onClick={() => onReject(user.id)}
												disabled={savingId === user.id}
												title="Rejeter et supprimer ce compte"
											>
												<X size={14} /> Rejeter
											</button>
										</span>
									</div>
								))}
							</>
						)}
					</div>
				) : (
					<div className="admin-users-table">
						<div className="admin-users-head">
							<span>Utilisateur</span>
							<span>Email</span>
							<span>Role</span>
							<span>Statut</span>
							<span>Approbation</span>
							<span>Actions</span>
						</div>
						{sortedUsers.map((user) => {
							const isSelf = currentUser?.id === user.id;
							const isEffectivelyActive = Boolean(user.is_active && user.is_approved);

							return (
								<div key={user.id} className="admin-users-row">
									<span className="admin-user-name">
										<UserRound size={15} /> {user.username} {isSelf ? '(vous)' : ''}
									</span>
									<span>{user.email || '-'}</span>
									<span>
										<span
											className={`admin-role-pill ${user.role === 'admin' ? 'is-admin' : ''}`}
										>
											{user.role}
										</span>
									</span>
									<span>
										<span
											className={`admin-status-pill ${isEffectivelyActive ? 'is-active' : 'is-inactive'}`}
										>
											{isEffectivelyActive ? 'Actif' : 'Inactif'}
										</span>
									</span>
									<span>
										<span
											className={`admin-status-pill ${user.is_approved ? 'is-approved' : 'is-pending'}`}
										>
											{user.is_approved ? 'Approuve' : 'En attente'}
										</span>
									</span>
									<span className="admin-actions">
										<button
											type="button"
											className="table-action"
											onClick={() => openView(user.id)}
											disabled={savingId === user.id}
										>
											<Eye size={14} /> Voir
										</button>
										<button
											type="button"
											className="table-action"
											onClick={() => openEdit(user)}
											disabled={savingId === user.id}
										>
											<PencilLine size={14} /> Modifier
										</button>
										<button
											type="button"
											className="table-action danger"
											onClick={() => onDelete(user.id)}
											disabled={savingId === user.id || isSelf}
										>
											<Trash2 size={14} /> Supprimer
										</button>
									</span>
								</div>
							);
						})}
					</div>
				)}
			</section>

			{viewUser && (
				<div className="admin-modal-overlay" onClick={() => setViewUser(null)}>
					<div className="admin-modal" onClick={(event) => event.stopPropagation()}>
						<div className="admin-modal-head">
							<h2>Details utilisateur</h2>
							<button type="button" className="admin-modal-close" onClick={() => setViewUser(null)}>
								Fermer
							</button>
						</div>
						<div className="admin-view-grid">
							<div>
								<p className="admin-view-label">ID</p>
								<p>{viewUser.id}</p>
							</div>
							<div>
								<p className="admin-view-label">Nom utilisateur</p>
								<p>{viewUser.username}</p>
							</div>
							<div>
								<p className="admin-view-label">Email</p>
								<p>{viewUser.email || '-'}</p>
							</div>
							<div>
								<p className="admin-view-label">Role</p>
								<p>{viewUser.role}</p>
							</div>
							<div>
								<p className="admin-view-label">Statut</p>
								<p>{viewUser.is_active && viewUser.is_approved ? 'Actif' : 'Inactif'}</p>
							</div>
							<div>
								<p className="admin-view-label">Email verifie</p>
								<p>{viewUser.is_email_verified ? 'Oui' : 'Non'}</p>
							</div>
							<div>
								<p className="admin-view-label">Approuve</p>
								<p>{viewUser.is_approved ? 'Oui' : 'Non'}</p>
							</div>
							<div>
								<p className="admin-view-label">Date creation</p>
								<p>{viewUser.created_at ? new Date(viewUser.created_at).toLocaleString() : '-'}</p>
							</div>
						</div>
					</div>
				</div>
			)}

			{editUserId && (
				<div className="admin-modal-overlay" onClick={closeEdit}>
					<div className="admin-modal" onClick={(event) => event.stopPropagation()}>
						<div className="admin-modal-head">
							<h2>Modifier utilisateur</h2>
							<button type="button" className="admin-modal-close" onClick={closeEdit}>
								Fermer
							</button>
						</div>
						<form className="auth-form" onSubmit={onEditSubmit}>
							<div className="form-group">
								<label htmlFor="admin-edit-username">Nom utilisateur</label>
								<input
									id="admin-edit-username"
									type="text"
									className="form-input"
									value={editForm.username}
									onChange={(event) =>
										setEditForm((prev) => ({ ...prev, username: event.target.value }))
									}
									required
								/>
							</div>
							<div className="form-group">
								<label htmlFor="admin-edit-email">Email</label>
								<input
									id="admin-edit-email"
									type="email"
									className="form-input"
									value={editForm.email}
									onChange={(event) =>
										setEditForm((prev) => ({ ...prev, email: event.target.value }))
									}
									required
								/>
							</div>
							<div className="form-group">
								<label htmlFor="admin-edit-role">Role</label>
								<div id="admin-edit-role" className="admin-role-toggle" role="radiogroup" aria-label="Role">
									<button
										type="button"
										className={`admin-role-option ${editForm.role === 'user' ? 'active' : ''}`}
										onClick={() => setEditForm((prev) => ({ ...prev, role: 'user' }))}
										aria-pressed={editForm.role === 'user'}
									>
										Utilisateur
									</button>
									<button
										type="button"
										className={`admin-role-option ${editForm.role === 'admin' ? 'active' : ''}`}
										onClick={() => setEditForm((prev) => ({ ...prev, role: 'admin' }))}
										aria-pressed={editForm.role === 'admin'}
									>
										Administrateur
									</button>
								</div>
							</div>
							<div className="admin-modal-actions">
								<button type="button" className="table-action admin-cancel-btn" onClick={closeEdit}>
									Annuler
								</button>
								<button
									type="submit"
									className="auth-button admin-save-btn"
									disabled={savingId === editUserId}
								>
									{savingId === editUserId ? 'Mise a jour...' : 'Enregistrer'}
								</button>
							</div>
						</form>
					</div>
				</div>
			)}
		</div>
	);
}

export default AdminUsersPage;
