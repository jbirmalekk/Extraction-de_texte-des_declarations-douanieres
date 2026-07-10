import { useCallback, useEffect, useMemo, useState } from 'react';
import {
	ArrowRight,
	Clock,
	Download,
	FileText,
	GitCompare,
	RefreshCw,
	Receipt,
	Search,
	ShieldCheck,
	Trash2,
	Users,
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/shared/hooks/useAuth';
import {
	deleteHistoryRows,
	fetchUnifiedHistoryBatch,
	HISTORY_BATCH_SIZE,
} from '@/shared/services/historyService';
import {
	computeHistoryStats,
	exportHistoryToCsv,
	filterHistoryRows,
	mergeHistoryRows,
} from '@/shared/utils/historyUnified';
import { beginReconciliationSession } from '@/shared/utils/crossVerificationSession';
import {
	hydrateDumContextFromApi,
	hydrateInvoiceContextFromApi,
} from '@/shared/utils/documentContextStorage';
import ErpExportButton from '@/features/erp/components/ErpExportButton';
import DocRefCell from '@/shared/components/ui/DocRefCell';
import DocTypeBadge from '@/shared/components/ui/DocTypeBadge';
import EmptyState from '@/shared/components/ui/EmptyState';
import ReconciliationCell from '@/shared/components/ui/ReconciliationCell';
import PageHeader from '@/shared/components/ui/PageHeader';
import StatCard from '@/shared/components/ui/StatCard';
import StatusBadge from '@/shared/components/ui/StatusBadge';
import {
	getHistoryErpExportTarget,
	historyReportInvoiceId,
	isReconciliationNeedsRedo,
	showHistoryErpExportButton,
	showHistoryReconcileButton,
	showHistoryReportLink,
	showHistoryValidationButton,
} from '@/shared/utils/workflowActions';
import './HistoryPage.css';

function HistoryRowActions({
	row,
	openingValidationId,
	onOpenValidation,
	onStartCrossVerify,
	isAdmin,
	onErpError,
}) {
	const reportInvoiceId = historyReportInvoiceId(row);
	const erpTarget = getHistoryErpExportTarget(row);
	const detailTo = row.type === 'dum' ? `/documents/${row.dumId}` : `/invoices/${row.invoiceId}`;

	return (
		<>
			<Link className="table-action table-action--detail" to={detailTo}>
				Détail
			</Link>
			{showHistoryValidationButton(row) ? (
				<button
					type="button"
					className="table-action table-action--btn table-action--validation"
					disabled={openingValidationId === row.id}
					onClick={() => onOpenValidation(row)}
				>
					{openingValidationId === row.id ? 'Chargement…' : 'Validation'}
				</button>
			) : null}
			{showHistoryReportLink(row) ? (
				<Link
					className="table-action table-action--btn table-action--report"
					to={`/reports/${reportInvoiceId}`}
				>
					Voir le rapport
				</Link>
			) : null}
			{showHistoryReconcileButton(row) ? (
				<button
					type="button"
					className="table-action table-action--btn table-action--reconcile"
					onClick={() => onStartCrossVerify(row)}
					title={
						isReconciliationNeedsRedo(row.controleStatut)
							? 'Choisir un autre document partenaire et relancer la comparaison'
							: undefined
					}
				>
					{isReconciliationNeedsRedo(row.controleStatut)
						? 'Refaire réconciliation'
						: 'Réconciliation'}
				</button>
			) : null}
			{showHistoryErpExportButton(row) && erpTarget ? (
				<ErpExportButton
					kind={erpTarget.kind}
					invoiceId={erpTarget.invoiceId}
					dumId={erpTarget.dumId}
					documentId={erpTarget.documentId}
					reference={erpTarget.reference}
					statutControle={erpTarget.statutControle}
					isAmountAligned={erpTarget.isAmountAligned !== false}
					isAdmin={isAdmin}
					onError={onErpError}
					className="table-action table-action--btn table-action--erp"
				>
					ERP
				</ErpExportButton>
			) : null}
		</>
	);
}

function HistoryPage() {
	const navigate = useNavigate();
	const { user } = useAuth();
	const isAdmin = user?.role === 'admin';

	const [dumHistory, setDumHistory] = useState([]);
	const [invoiceItems, setInvoiceItems] = useState([]);
	const [dumTotal, setDumTotal] = useState(0);
	const [invoiceTotal, setInvoiceTotal] = useState(0);
	const [ownerCount, setOwnerCount] = useState(0);
	const [loading, setLoading] = useState(true);
	const [loadingMore, setLoadingMore] = useState(false);
	const [error, setError] = useState('');
	const [search, setSearch] = useState('');
	const [typeFilter, setTypeFilter] = useState('all');
	const [statusFilter, setStatusFilter] = useState('all');
	const [periodDays, setPeriodDays] = useState(0);
	const [openingValidationId, setOpeningValidationId] = useState(null);
	const [selectedIds, setSelectedIds] = useState(() => new Set());
	const [deleting, setDeleting] = useState(false);

	const allRows = useMemo(
		() => mergeHistoryRows(dumHistory, invoiceItems),
		[dumHistory, invoiceItems]
	);

	const hasMoreFromApi =
		dumHistory.length < dumTotal || invoiceItems.length < invoiceTotal;

	const loadHistory = useCallback(async () => {
		setLoading(true);
		setError('');
		try {
			const page = await fetchUnifiedHistoryBatch({
				skip: 0,
				limit: HISTORY_BATCH_SIZE,
				type: 'all',
			});
			setDumHistory(page.dumHistory);
			setInvoiceItems(page.invoiceItems);
			setDumTotal(page.dumTotal);
			setInvoiceTotal(page.invoiceTotal);
			setOwnerCount(page.ownerCount);
			if (page.invoiceSource === 'error' || page.invoiceSource === 'unavailable') {
				setError(
					'Historique DUM chargé. Les factures sont indisponibles — démarrez back_EMP_Fact (8001) et vérifiez INVOICE_API_URL dans back_EMP.'
				);
			}
		} catch {
			setError(
				'Impossible de charger l’historique. Vérifiez que back_EMP (8000) et back_EMP_Fact (8001) sont démarrés.'
			);
		} finally {
			setLoading(false);
		}
	}, []);

	const loadMoreFromApi = async () => {
		if (!hasMoreFromApi || loadingMore) {
			return;
		}
		setLoadingMore(true);
		try {
			const skip = dumHistory.length + invoiceItems.length;
			const page = await fetchUnifiedHistoryBatch({
				skip,
				limit: HISTORY_BATCH_SIZE,
				type: 'all',
			});
			if (page.dumHistory.length) {
				setDumHistory((prev) => [...prev, ...page.dumHistory]);
				setDumTotal(page.dumTotal);
			}
			if (page.invoiceItems.length) {
				setInvoiceItems((prev) => [...prev, ...page.invoiceItems]);
				setInvoiceTotal(page.invoiceTotal);
			}
		} finally {
			setLoadingMore(false);
		}
	};

	useEffect(() => {
		loadHistory();
	}, [loadHistory]);

	const filteredRows = useMemo(
		() =>
			filterHistoryRows(allRows, {
				search: search.trim(),
				type: typeFilter,
				status: statusFilter,
				periodDays,
			}),
		[allRows, search, typeFilter, statusFilter, periodDays]
	);

	const stats = useMemo(
		() => computeHistoryStats(filteredRows, { isAdmin, ownerCount }),
		[filteredRows, isAdmin, ownerCount]
	);

	const statCards = [
		{
			key: 'total',
			label: 'Total traitements',
			value: stats.total,
			icon: FileText,
			color: '#2563eb',
			hint: 'DUM + factures',
		},
		{
			key: 'validated',
			label: 'Validés / contrôlés',
			value: stats.validated,
			icon: ShieldCheck,
			color: '#16a34a',
			hint: 'Prêts pour réconciliation',
			to: '/history',
		},
		{
			key: 'inProgress',
			label: 'En attente / cours',
			value: stats.inProgress,
			icon: Clock,
			color: '#f59e0b',
			hint: 'Action requise',
		},
		{
			key: 'recon',
			label: 'Réconciliations OK',
			value: stats.reconciledOk,
			icon: GitCompare,
			color: '#0f766e',
			hint: `${stats.reconciledWarn} avec écarts`,
			to: '/reports',
		},
	];
	if (isAdmin) {
		statCards.push({
			key: 'owners',
			label: 'Utilisateurs',
			value: stats.owners ?? ownerCount,
			icon: Users,
			color: '#7c3aed',
		});
	}

	const handleExportCsv = () => {
		const csv = exportHistoryToCsv(filteredRows);
		const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `historique_emp_${new Date().toISOString().slice(0, 10)}.csv`;
		a.click();
		URL.revokeObjectURL(url);
	};

	const openValidation = async (row) => {
		const rowKey = row.id;
		setOpeningValidationId(rowKey);
		setError('');
		try {
			if (row.type === 'dum') {
				if (!row.dumId) {
					setError('Identifiant DUM manquant pour ce document.');
					return;
				}
				await hydrateDumContextFromApi(row.dumId);
				navigate(`/validation?documentId=${row.dumId}`, {
					state: { fromHistory: true, documentId: row.dumId },
				});
			} else {
				if (!row.invoiceId) {
					setError('Identifiant facture manquant pour ce document.');
					return;
				}
				await hydrateInvoiceContextFromApi(row.invoiceId);
				navigate(`/invoice-validation?invoiceId=${row.invoiceId}`, {
					state: { fromHistory: true, invoiceId: row.invoiceId },
				});
			}
		} catch (err) {
			const detail = err?.response?.data?.detail;
			setError(
				typeof detail === 'string'
					? detail
					: 'Impossible de charger ce document pour la validation.'
			);
		} finally {
			setOpeningValidationId(null);
		}
	};

	const selectedCount = selectedIds.size;
	const filteredSelectedCount = filteredRows.filter((r) => selectedIds.has(r.id)).length;
	const allFilteredSelected =
		filteredRows.length > 0 && filteredSelectedCount === filteredRows.length;

	const toggleRowSelection = (rowId) => {
		setSelectedIds((prev) => {
			const next = new Set(prev);
			if (next.has(rowId)) {
				next.delete(rowId);
			} else {
				next.add(rowId);
			}
			return next;
		});
	};

	const toggleSelectAllFiltered = () => {
		if (allFilteredSelected) {
			setSelectedIds((prev) => {
				const next = new Set(prev);
				for (const row of filteredRows) {
					next.delete(row.id);
				}
				return next;
			});
			return;
		}
		setSelectedIds((prev) => {
			const next = new Set(prev);
			for (const row of filteredRows) {
				next.add(row.id);
			}
			return next;
		});
	};

	const handleDeleteSelected = async () => {
		const rowsToDelete = filteredRows.filter((r) => selectedIds.has(r.id));
		if (!rowsToDelete.length) {
			return;
		}
		const label = rowsToDelete.length === 1 ? 'cet enregistrement' : `${rowsToDelete.length} enregistrements`;
		if (
			!window.confirm(
				`Supprimer définitivement ${label} ?\n\nLes fichiers locaux et les données en base seront effacés. Action irréversible.`
			)
		) {
			return;
		}
		setDeleting(true);
		setError('');
		try {
			const result = await deleteHistoryRows(rowsToDelete, user);
			const failed =
				(result.dum?.failed?.length || 0) + (result.invoice?.failed?.length || 0);
			const deleted =
				(result.dum?.deleted?.length || 0) + (result.invoice?.deleted?.length || 0);
			setSelectedIds(new Set());
			await loadHistory();
			if (failed > 0 && deleted > 0) {
				setError(`${deleted} supprimé(s), ${failed} refusé(s) ou introuvable(s).`);
			} else if (failed > 0) {
				setError('Aucune suppression effectuée (accès refusé ou introuvable).');
			}
		} catch {
			setError('Échec de la suppression. Vérifiez les serveurs (8000 / 8001).');
		} finally {
			setDeleting(false);
		}
	};

	const startCrossVerify = (row) => {
		if (row.type === 'dum') {
			beginReconciliationSession({
				sourceType: 'dum',
				sourceId: row.dumId,
				sourceNumero: row.reference,
				sourceDate: row.declarationDate || null,
				sourceLabel: row.reference,
				sourceFileName: row.fileName || row.reference,
			});
		} else {
			beginReconciliationSession({
				sourceType: 'invoice',
				sourceId: row.invoiceId,
				sourceNumero: row.reference,
				sourceDate: row.invoiceDate || null,
				sourceLabel: row.reference,
				sourceFileName: row.fileName || row.reference,
			});
		}
		navigate('/cross-verification');
	};

	return (
		<div className="history-page history-page--unified fade-up">
			<PageHeader
				kicker="Centre de pilotage"
				title={isAdmin ? 'Historique DUM & factures' : 'Mon historique'}
				subtitle="Vue unifiée : statuts, réconciliation (partenaire DUM ou facture) et actions rapides."
			/>

			{error ? (
				<section className="activities history-empty">
					<p>{error}</p>
					<button type="button" className="history-btn ghost" onClick={loadHistory}>
						Réessayer
					</button>
				</section>
			) : null}

			<section className="emp-stats-grid history-stats-grid">
				{statCards.map(({ key, label, value, icon, color, hint, to }) => (
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

			<section className="history-filters-card">
				<div className="history-search-wrap">
					<Search size={18} />
					<input
						type="search"
						placeholder="Rechercher n° déclaration, facture, fichier…"
						value={search}
						onChange={(e) => setSearch(e.target.value)}
					/>
				</div>
				<div className="history-filters-row">
					<label>
						Type
						<select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
							<option value="all">Tous</option>
							<option value="dum">DUM</option>
							<option value="invoice">Facture</option>
						</select>
					</label>
					<label>
						Statut
						<select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
							<option value="all">Tous</option>
							<option value="validated">Validé / contrôlé</option>
							<option value="in_progress">En cours</option>
							<option value="rejected">Rejeté</option>
							<option value="reconciled">Réconcilié</option>
						</select>
					</label>
					<label>
						Période
						<select
							value={periodDays}
							onChange={(e) => setPeriodDays(Number(e.target.value))}
						>
							<option value={0}>Tout</option>
							<option value={7}>7 jours</option>
							<option value={30}>30 jours</option>
						</select>
					</label>
					<button type="button" className="history-btn ghost" onClick={loadHistory} disabled={loading}>
						<RefreshCw size={16} />
						Actualiser
					</button>
					<button
						type="button"
						className="history-btn outline"
						onClick={handleExportCsv}
						disabled={loading || filteredRows.length === 0}
					>
						<Download size={16} />
						Export CSV
					</button>
					{selectedCount > 0 ? (
						<button
							type="button"
							className="history-btn danger"
							onClick={handleDeleteSelected}
							disabled={loading || deleting}
						>
							<Trash2 size={16} />
							{deleting ? 'Suppression…' : `Supprimer (${selectedCount})`}
						</button>
					) : null}
				</div>
			</section>

			<section className="emp-panel history-section">
				<div className="emp-panel-head">
					<h2>{isAdmin ? 'Historique complet' : 'Mes activités'}</h2>
					<span className="history-count">
						{loading
							? 'Chargement…'
							: `${filteredRows.length} / ${allRows.length} enregistrement${allRows.length > 1 ? 's' : ''}`}
					</span>
				</div>
				<div className="emp-panel-body">
				<div className="history-table history-table--unified">
					<div className="history-table-head">
						<span className="history-select-head">
							<input
								type="checkbox"
								checked={allFilteredSelected}
								disabled={loading || filteredRows.length === 0}
								onChange={toggleSelectAllFiltered}
								aria-label="Tout sélectionner (filtre actuel)"
							/>
						</span>
						<span>Type</span>
						<span>Référence / fichier</span>
						{isAdmin ? <span>Propriétaire</span> : <span>—</span>}
						<span>Date</span>
						<span>Statut</span>
						<span>Réconciliation</span>
						<span>Corr.</span>
						<span>Actions</span>
					</div>

					{loading ? (
						<div className="history-table-row history-loading-row">
							<span colSpan="8">Chargement…</span>
						</div>
					) : filteredRows.length > 0 ? (
						filteredRows.map((row) => (
							<div
								key={row.id}
								className={`history-table-row${selectedIds.has(row.id) ? ' history-table-row--selected' : ''}`}
							>
								<span className="history-select-cell">
									<input
										type="checkbox"
										checked={selectedIds.has(row.id)}
										onChange={() => toggleRowSelection(row.id)}
										aria-label={`Sélectionner ${row.reference}`}
									/>
								</span>
								<span>
									<DocTypeBadge type={row.type} />
								</span>
								<span>
									<DocRefCell
										numero={row.reference}
										date={
											row.type === 'dum'
												? row.declarationDate
												: row.invoiceDate
										}
										fileName={row.fileName}
									/>
								</span>
								<span>{isAdmin ? row.owner || '—' : 'Moi'}</span>
								<span className="history-date-cell">{row.dateLabel}</span>
								<span>
									<StatusBadge label={row.status} tone={row.statusTone} />
								</span>
								<span>
									<ReconciliationCell
										statusLabel={row.reconciliationStatusLabel}
										statusTone={row.reconciliationStatusTone}
										partnerType={row.reconciliationPartnerType}
										partnerNumero={row.reconciliationPartnerNumero}
										partnerDate={row.reconciliationPartnerDate}
									/>
								</span>
								<span className="history-corr-cell" title={row.correctionsHint || ''}>
									{row.correctionsCount}
								</span>
								<span className="history-actions-cell">
									<HistoryRowActions
										row={row}
										openingValidationId={openingValidationId}
										onOpenValidation={openValidation}
										onStartCrossVerify={startCrossVerify}
										isAdmin={isAdmin}
										onErpError={setError}
									/>
								</span>
							</div>
						))
					) : (
						<EmptyState
							title="Aucun enregistrement"
							message="Aucun document ne correspond aux filtres actuels."
							actions={
								<Link to="/import" className="history-btn primary">
									Importer un document <ArrowRight size={14} />
								</Link>
							}
						/>
					)}
				</div>
				</div>

				{!loading && hasMoreFromApi ? (
					<div className="history-load-more">
						<button
							type="button"
							className="history-btn ghost"
							onClick={loadMoreFromApi}
							disabled={loadingMore}
						>
							{loadingMore
								? 'Chargement…'
								: `Charger plus (DUM ${dumHistory.length}/${dumTotal} · Factures ${invoiceItems.length}/${invoiceTotal})`}
						</button>
					</div>
				) : null}
			</section>
		</div>
	);
}

export default HistoryPage;
