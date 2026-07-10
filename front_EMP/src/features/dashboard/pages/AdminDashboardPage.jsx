import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, CheckCircle, Clock, Database, FileText, ShieldCheck, Users } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/shared/hooks/useAuth';
import { fetchUnifiedHistoryBatch } from '@/shared/services/historyService';
import { fetchAdminDashboard } from '@/shared/services/ocrService';

const DEFAULT_STATS = [
  { key: 'documents_processed', label: 'Documents traités', icon: FileText, color: '#2563eb' },
  { key: 'validated_this_month', label: 'Validés ce mois', icon: CheckCircle, color: '#16a34a' },
  { key: 'pending_validation', label: 'En attente de validation', icon: Clock, color: '#f59e0b' },
  { key: 'ready_for_erp', label: 'Prêts pour ERP', icon: Database, color: '#8b5cf6' },
  { key: 'total_users', label: 'Utilisateurs total', icon: Users, color: '#0f766e' },
  { key: 'admin_users', label: 'Administrateurs', icon: ShieldCheck, color: '#be123c' },
];

function AdminDashboardPage() {
	const { user } = useAuth();
	const navigate = useNavigate();
	const [dashboard, setDashboard] = useState({ stats: {}, monthly_indicators: [], recent_activity: [] });
	const [recentUnified, setRecentUnified] = useState([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState('');

	useEffect(() => {
		if (user && user.role !== 'admin') {
			navigate('/dashboard', { replace: true });
		}
	}, [navigate, user]);

	useEffect(() => {
		let isActive = true;

		const loadDashboard = async () => {
			setLoading(true);
			setError('');
			try {
				const [data, unified] = await Promise.all([
					fetchAdminDashboard(),
					fetchUnifiedHistoryBatch({ isAdmin: true, user }).catch(() => ({ rows: [] })),
				]);
				if (isActive) {
					setDashboard(data || { stats: {}, monthly_indicators: [], recent_activity: [] });
					setRecentUnified((unified?.rows || []).slice(0, 5));
				}
			} catch (_fetchError) {
				if (isActive) {
					setError('Impossible de charger le tableau de bord administrateur.');
				}
			} finally {
				if (isActive) {
					setLoading(false);
				}
			}
		};

		loadDashboard();

		return () => {
			isActive = false;
		};
	}, []);

	const stats = useMemo(
		() =>
			DEFAULT_STATS.map((item) => ({
				...item,
				value: dashboard?.stats?.[item.key] ?? 0,
			})),
		[dashboard],
	);

	const monthlyIndicators = dashboard?.monthly_indicators || [];
	const activities = dashboard?.recent_activity || [];
	const recentRows =
		recentUnified.length > 0
			? recentUnified
			: activities.map((a) => ({
					id: `dum-${a.document_id}`,
					type: 'dum',
					typeLabel: 'DUM',
					reference: a.document,
					dateLabel: a.date,
					status: a.status,
					statusTone: a.tone,
					owner: a.owner,
					dumId: a.document_id,
					invoiceId: null,
				}));
	const monthlyPeak = useMemo(
		() => Math.max(1, ...monthlyIndicators.map((item) => Number(item.documents_processed || 0))),
		[monthlyIndicators],
	);

	return (
		<section className="dashboard-page admin-dashboard-page">
			<section className="dashboard-hero modern admin-hero">
				<div className="dashboard-hero-copy">
					<p className="hero-pill">Administration</p>
					<h1>Tableau de bord</h1>
					<p className="subtitle">Vue globale des utilisateurs, validations et documents traités.</p>
				</div>
				<Link to="/admin/users" className="hero-import-btn">
					<ShieldCheck size={18} />
					Gérer les utilisateurs
				</Link>
			</section>

			{error ? (
				<section className="activities history-empty">
					<p>{error}</p>
				</section>
			) : null}

			<section className="stats-grid">
				{stats.map(({ label, value, icon: Icon, color }) => (
					<div key={label} className="stat-card">
						<div className="stat-icon" style={{ color, backgroundColor: `${color}15` }}>
							<Icon size={20} />
						</div>
						<div>
							<p className="stat-label">{label}</p>
							<p className="stat-value">{loading ? '…' : value}</p>
						</div>
					</div>
				))}
			</section>

			<section className="activities">
				<div className="section-header">
					<h2>Indicateurs mensuels</h2>
				</div>
				<div className="month-mini-grid">
					{monthlyIndicators.map((item) => (
						<article key={item.month} className="month-mini-card">
							<div className="month-mini-card-head">
								<div>
									<p className="month-mini-label">{item.label}</p>
									<h3>{item.month}</h3>
								</div>
								<span className="month-mini-chip">{item.documents_processed} docs</span>
							</div>
							<div className="month-mini-track" aria-hidden="true">
								<span
									className="month-mini-fill"
									style={{ width: `${(Number(item.documents_processed || 0) / monthlyPeak) * 100}%` }}
								/>
							</div>
							<div className="month-mini-values">
								<div>
									<strong>{item.documents_processed}</strong>
									<small>documents traités</small>
								</div>
								<div>
									<strong>{item.validated}</strong>
									<small>validés</small>
								</div>
							</div>
						</article>
					))}
				</div>
			</section>

			<section className="activities">
				<div className="section-header">
					<h2>Activité récente</h2>
					<Link to="/history" className="text-link">Voir l’historique</Link>
				</div>
				<div className="activity-table">
					<div className="table-head">
						<span>Type</span>
						<span>Document</span>
						<span>Propriétaire</span>
						<span>Date</span>
						<span>Statut</span>
						<span>Action</span>
					</div>
					{loading ? (
						<div className="table-row">
							<span>—</span>
							<span>Chargement…</span>
							<span>—</span>
							<span>—</span>
							<span><span className="status-pill warning">…</span></span>
							<span>—</span>
						</div>
					) : recentRows.length > 0 ? (
						recentRows.map((row) => (
							<div key={row.id} className="table-row">
								<span>{row.typeLabel || 'DUM'}</span>
								<span>{row.reference}</span>
								<span>{row.owner || (row.type === 'invoice' ? '—' : '—')}</span>
								<span>{row.dateLabel || row.date}</span>
								<span>
									<span className={`status-pill ${row.statusTone || row.tone}`}>{row.status}</span>
								</span>
								<span>
									<Link
										className="table-action"
										to={
											row.type === 'invoice'
												? `/invoices/${row.invoiceId}`
												: `/documents/${row.dumId}`
										}
									>
										Voir <ArrowRight size={14} />
									</Link>
								</span>
							</div>
						))
					) : (
						<div className="table-row">
							<span>—</span>
							<span>Aucune activité</span>
							<span>—</span>
							<span>—</span>
							<span><span className="status-pill info">Vide</span></span>
							<span>—</span>
						</div>
					)}
				</div>
			</section>
		</section>
	);
}

export default AdminDashboardPage;