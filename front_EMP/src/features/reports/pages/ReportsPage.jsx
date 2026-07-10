import { useCallback, useEffect, useMemo, useState } from 'react';
import { Eye, GitCompare, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import DocRefCell from '../components/ui/DocRefCell';
import EmptyState from '../components/ui/EmptyState';
import PageHeader from '../components/ui/PageHeader';
import StatCard from '../components/ui/StatCard';
import StatusBadge from '../components/ui/StatusBadge';
import { useAuth } from '../hooks/useAuth';
import { fetchInvoicesList } from '../services/invoiceApi';
import { buildCompactDocParts } from '../utils/crossVerifyDisplay';
import { formatHistoryDateTime } from '../utils/historyUnified';
import { computeReportsStats } from '../utils/workflowProgress';
import './ReportsPage.css';

const controleLabel = (sc) => {
	if (sc === 'ok') {
		return { label: 'Conforme', tone: 'ok' };
	}
	if (sc === 'warning') {
		return { label: 'Attention', tone: 'warning' };
	}
	if (sc === 'error') {
		return { label: 'Écart', tone: 'error' };
	}
	return { label: '—', tone: 'neutral' };
};

function ReportsPage() {
	const { user } = useAuth();
	const [items, setItems] = useState([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState('');

	const loadReports = useCallback(async () => {
		setLoading(true);
		setError('');
		try {
			const page = await fetchInvoicesList({ limit: 200 }, user);
			const compared = (page.items || []).filter(
				(inv) => inv.compared_at || inv.statut_controle
			);
			setItems(compared);
		} catch {
			setError('Impossible de charger les rapports (vérifiez back_EMP_Fact sur le port 8001).');
		} finally {
			setLoading(false);
		}
	}, [user]);

	useEffect(() => {
		loadReports();
	}, [loadReports]);

	const reportStats = useMemo(() => computeReportsStats(items), [items]);

	const tableRows = useMemo(
		() =>
			items.map((inv) => {
				const st = controleLabel(inv.statut_controle);
				return {
					id: inv.id,
					facture: buildCompactDocParts(
						inv.numero_facture,
						inv.date_facture,
						inv.id,
						'FACT'
					),
					dum: buildCompactDocParts(
						inv.numero_declaration_dum,
						inv.date_declaration_dum,
						inv.dum_document_id,
						'DUM'
					),
					dumId: inv.dum_document_id,
					statutControle: inv.statut_controle,
					statutLabel: st.label,
					statutTone: st.tone,
					pfnDum: inv.montant_declare_dum,
					netPay: inv.net_pay,
					ecart: inv.ecart_montant,
					devise: inv.devise_declaree_dum || inv.devise || '',
					comparedAt: formatHistoryDateTime(inv.compared_at),
				};
			}),
		[items]
	);

	return (
		<div className="reports-page fade-up">
			<PageHeader
				kicker="Centre de pilotage — Contrôles"
				title="Rapports de vérification"
				subtitle="Synthèse des dossiers DUM ↔ facture : montants, statuts et accès au rapport détaillé ou à l’export ERP."
				actions={
					<>
						<button
							type="button"
							className="reports-btn ghost"
							onClick={loadReports}
							disabled={loading}
						>
							<RefreshCw size={16} />
							Actualiser
						</button>
						<Link to="/cross-verification" className="reports-btn primary">
							<GitCompare size={16} />
							Nouveau contrôle
						</Link>
					</>
				}
			/>

			{error ? (
				<section className="reports-card reports-error">
					<p>{error}</p>
				</section>
			) : null}

			<section className="emp-stats-grid">
				<StatCard
					label="Contrôles enregistrés"
					value={reportStats.total}
					icon={GitCompare}
					color="#2563eb"
					loading={loading}
				/>
				<StatCard
					label="Conformes"
					value={reportStats.ok}
					icon={Eye}
					color="#16a34a"
					hint="Prêts export dossier ERP"
					loading={loading}
				/>
				<StatCard
					label="Attention"
					value={reportStats.warn}
					color="#d97706"
					loading={loading}
				/>
				<StatCard
					label="Écarts"
					value={reportStats.err}
					color="#dc2626"
					hint="Réconciliation à refaire"
					loading={loading}
				/>
			</section>

			<section className="emp-panel reports-panel">
				<div className="emp-panel-head">
					<h2>Dossiers contrôlés</h2>
				</div>
				<div className="emp-panel-body">
					<div className="reports-table-head reports-table-head--rich">
						<span className="reports-col-title">
							Facture
							<small>N° · date</small>
						</span>
						<span className="reports-col-title">
							DUM liée
							<small>N° · date</small>
						</span>
						<span className="reports-col-title">
							Statut
							<small>Contrôle</small>
						</span>
						<span className="reports-col-title">
							Date
							<small>Comparaison</small>
						</span>
						<span className="reports-col-title">
							Actions
							<small>Rapport</small>
						</span>
					</div>

					{loading ? (
						<p className="reports-empty">Chargement…</p>
					) : tableRows.length === 0 ? (
						<EmptyState
							title="Aucun contrôle"
							message="Lancez une vérification croisée pour générer des rapports."
							actions={
								<Link to="/cross-verification" className="reports-btn primary">
									Vérification croisée
								</Link>
							}
						/>
					) : (
						tableRows.map((row) => (
							<div key={row.id} className="reports-table-row reports-table-row--rich">
								<DocRefCell
									numero={row.facture.numero}
									date={row.facture.date}
								/>
								<DocRefCell numero={row.dum.numero} date={row.dum.date} />
								<span className="reports-cell-statut">
									<StatusBadge label={row.statutLabel} tone={row.statutTone} />
								</span>
								<span className="reports-date">{row.comparedAt}</span>
								<span className="reports-actions">
									<Link to={`/reports/${row.id}`} className="reports-btn primary small">
										<Eye size={14} />
										Rapport
									</Link>
								</span>
							</div>
						))
					)}
				</div>
			</section>
		</div>
	);
}

export default ReportsPage;
