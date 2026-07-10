import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, CheckCircle, Clock, Database, FileText, FileUp, GitCompare } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import DocTypeBadge from '@/shared/components/ui/DocTypeBadge';
import EmptyState from '@/shared/components/ui/EmptyState';
import PageHeader from '@/shared/components/ui/PageHeader';
import StatCard from '@/shared/components/ui/StatCard';
import StatusBadge from '@/shared/components/ui/StatusBadge';
import WorkflowTimeline from '@/shared/components/ui/WorkflowTimeline';
import { useAuth } from '@/shared/hooks/useAuth';
import { fetchUnifiedHistoryBatch } from '@/shared/services/historyService';
import { fetchMyDashboard } from '@/shared/services/ocrService';
import { mergeHistoryRows } from '@/shared/utils/historyUnified';
import { getWorkflowProgressFromHistoryRow } from '@/shared/utils/workflowProgress';

const DEFAULT_STATS = [
	{
		key: 'documents_processed',
		label: 'Documents traités',
		icon: FileText,
		color: '#2563eb',
		hint: 'DUM importées',
	},
	{
		key: 'validated_this_month',
		label: 'Validés ce mois',
		icon: CheckCircle,
		color: '#16a34a',
		hint: 'Contrôles humains',
		to: '/history?status=validated',
	},
	{
		key: 'pending_validation',
		label: 'En attente',
		icon: Clock,
		color: '#f59e0b',
		hint: 'À valider',
		to: '/history?status=in_progress',
	},
	{
		key: 'ready_for_erp',
		label: 'Prêts ERP',
		icon: Database,
		color: '#8b5cf6',
		hint: 'DUM validées',
		to: '/reports',
	},
];

function DashboardPage() {
	const { user } = useAuth();
	const navigate = useNavigate();
	const [dashboard, setDashboard] = useState({ stats: {}, recent_activity: [] });
	const [recentUnified, setRecentUnified] = useState([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState('');
	const monthlyIndicators = dashboard?.monthly_indicators || [];

	useEffect(() => {
		if (user?.role === 'admin') {
			navigate('/admin/dashboard', { replace: true });
		}
	}, [navigate, user?.role]);

	useEffect(() => {
		let isActive = true;

		const loadDashboard = async () => {
			setLoading(true);
			setError('');

			try {
				const [data, unified] = await Promise.all([
					fetchMyDashboard(),
					fetchUnifiedHistoryBatch({ skip: 0, limit: 8, type: 'all' }).catch(() => ({
						dumHistory: [],
						invoiceItems: [],
					})),
				]);
				if (isActive) {
					setDashboard(data || { stats: {}, recent_activity: [] });
					setRecentUnified(
						mergeHistoryRows(unified.dumHistory || [], unified.invoiceItems || []).slice(0, 6)
					);
				}
			} catch {
				if (isActive) {
					setError('Impossible de charger votre tableau de bord pour le moment.');
					setRecentUnified([]);
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
	}, [user]);

	const stats = useMemo(
		() =>
			DEFAULT_STATS.map((item) => ({
				...item,
				value: dashboard?.stats?.[item.key] ?? 0,
			})),
		[dashboard]
	);

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
					dumId: a.document_id,
					invoiceId: null,
					statusFilterKey: a.status === 'Validé' ? 'validated' : 'pending',
					isReconciled: false,
					controleStatut: null,
				}));

	const sampleProgress = getWorkflowProgressFromHistoryRow(
		recentRows[0] || { statusFilterKey: 'in_progress' }
	);

	const monthlyPeak = useMemo(
		() => Math.max(1, ...monthlyIndicators.map((item) => Number(item.documents_processed || 0))),
		[monthlyIndicators]
	);

	return (
		<div className="fade-up">
			<PageHeader
				kicker="Pilotage OCR"
				title="Tableau de bord"
				subtitle={
					user?.username
						? `Bonjour ${user.username} — synthèse imports, validations, réconciliations et exports ERP.`
						: 'Visualisez vos indicateurs et accédez aux actions prioritaires.'
				}
				actions={
					<Link to="/import" className="hero-import-btn">
						<FileUp size={18} />
						Nouveau document
					</Link>
				}
			/>

			
			{error ? (
				<section className="activities history-empty">
					<p>{error}</p>
				</section>
			) : null}

			<section className="emp-stats-grid">
				{stats.map(({ key, label, value, icon, color, hint, to }) => (
					<StatCard
						key={key}
						label={label}
						value={value}
						hint={hint}
						icon={icon}
						color={color}
						to={to}
						loading={loading}
					/>
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
									style={{
										width: `${(Number(item.documents_processed || 0) / monthlyPeak) * 100}%`,
									}}
								/>
							</div>
							<div className="month-mini-values">
								<div>
									<strong>{item.documents_processed}</strong>
									<small>traités</small>
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

			<section className="emp-panel">
				<div className="emp-panel-head">
					<h2>Activité récente</h2>
					<Link to="/history" className="text-link">
						Centre de pilotage — Historique
					</Link>
				</div>
				<div className="emp-panel-body">
					<div className="activity-table activity-table--rich">
						<div className="table-head">
							<span>Type</span>
							<span>Document</span>
							<span>Date</span>
							<span>Statut</span>
							<span>Parcours</span>
							<span>Action</span>
						</div>
						{loading ? (
							<div className="table-row">
								<span colSpan="6">Chargement…</span>
							</div>
						) : recentRows.length > 0 ? (
							recentRows.map((row) => (
								<div key={row.id} className="table-row table-row--rich">
									<span>
										<DocTypeBadge type={row.type} />
									</span>
									<span className="emp-doc-ref">
										<strong>{row.reference}</strong>
										{row.fileName ? <small>{row.fileName}</small> : null}
									</span>
									<span>{row.dateLabel || '—'}</span>
									<span>
										<StatusBadge label={row.status} tone={row.statusTone} />
									</span>
									<span className="dashboard-mini-timeline">
										<WorkflowTimeline
											compact
											title=""
											steps={getWorkflowProgressFromHistoryRow(row)}
										/>
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
							<EmptyState
								title="Aucune activité"
								message="Importez une DUM ou une facture pour démarrer le parcours."
								actions={
									<>
										<Link to="/import" className="history-btn primary">
											Importer
										</Link>
										<Link to="/cross-verification" className="history-btn outline">
											<GitCompare size={14} /> Réconciliation
										</Link>
									</>
								}
							/>
						)}
					</div>
				</div>
			</section>
		</div>
	);
}

export default DashboardPage;
