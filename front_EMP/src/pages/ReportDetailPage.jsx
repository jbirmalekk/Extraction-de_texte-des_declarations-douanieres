import { useCallback, useEffect, useState } from 'react';
import {
	AlertTriangle,
	ArrowLeft,
	CheckCircle2,
	Clock,
	Download,
	FileText,
	RefreshCw,
	Shield,
	XCircle,
} from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { formatMoney } from '../utils/compareDisplay';
import { loadReportContext } from '../utils/reportContext';
import { exportComparisonReportPdf } from '../utils/reconciliationReportPdf';
import './ReportDetailPage.css';

function ReportDetailPage() {
	const { invoiceId } = useParams();
	const navigate = useNavigate();
	const [ctx, setCtx] = useState(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState('');
	const [exporting, setExporting] = useState(false);

	const load = useCallback(async () => {
		setLoading(true);
		setError('');
		try {
			const data = await loadReportContext(invoiceId);
			setCtx(data);
		} catch (err) {
			setError(
				err?.response?.data?.detail ||
					err?.message ||
					'Impossible de charger ce rapport.'
			);
			setCtx(null);
		} finally {
			setLoading(false);
		}
	}, [invoiceId]);

	useEffect(() => {
		load();
	}, [load]);

	const handleExportPdf = () => {
		if (!ctx) {
			return;
		}
		setExporting(true);
		try {
			exportComparisonReportPdf({
				comparison: ctx.invoice,
				dumDetail: ctx.dum,
				invoiceDetail: ctx.invoice,
				comparisonRows: ctx.comparisonRows,
				amountSummary: ctx.amountSummary,
				dossierRef: ctx.dossierRef,
				confidence: ctx.confidence,
				issueCount: ctx.issueCount,
			});
		} finally {
			setExporting(false);
		}
	};

	const openReconciliation = () => {
		if (!ctx?.invoiceId || !ctx?.dumId) {
			navigate('/cross-verification');
			return;
		}
		navigate('/cross-verification', {
			state: {
				fromReports: true,
				openReport: true,
				invoiceId: ctx.invoiceId,
				dumId: ctx.dumId,
			},
		});
	};

	if (loading) {
		return (
			<div className="report-detail-page">
				<p className="report-detail-loading">Chargement du rapport…</p>
			</div>
		);
	}

	if (error || !ctx) {
		return (
			<div className="report-detail-page">
				<Link to="/reports" className="report-detail-back">
					<ArrowLeft size={16} />
					Retour aux rapports
				</Link>
				<section className="report-detail-alert is-error">
					<AlertTriangle size={22} />
					<p>{error || 'Rapport introuvable.'}</p>
				</section>
			</div>
		);
	}

	const { invoice, dum, comparisonRows, amountSummary, issueCount, confidence, dossierRef } =
		ctx;
	const dev = amountSummary.devise || '';
	const hasAlert = !amountSummary.aligned || ctx.statutControle === 'error';
	const hasWarning = ctx.statutControle === 'warning' && !hasAlert;

	return (
		<div className="report-detail-page fade-up">
			<header className="report-detail-top">
				<div>
					<Link to="/reports" className="report-detail-back">
						<ArrowLeft size={16} />
						Rapports de contrôle
					</Link>
					<h1>Rapport de vérification croisée</h1>
					<p className="report-detail-sub">{dossierRef}</p>
				</div>
				<div className="report-detail-top-actions">
					<button type="button" className="rd-btn ghost" onClick={load}>
						<RefreshCw size={16} />
						Actualiser
					</button>
					<button
						type="button"
						className="rd-btn primary"
						onClick={handleExportPdf}
						disabled={exporting}
					>
						<Download size={16} />
						{exporting ? 'Export…' : 'Exporter PDF'}
					</button>
				</div>
			</header>

			<section
				className={`report-detail-alert ${hasAlert ? 'is-error' : hasWarning ? 'is-warn' : 'is-ok'}`}
			>
				{hasAlert ? <XCircle size={24} /> : hasWarning ? <AlertTriangle size={24} /> : <CheckCircle2 size={24} />}
				<div>
					<strong>
						{hasAlert
							? 'Alerte : écart détecté'
							: hasWarning
								? 'Attention : vérifications complémentaires'
								: 'Contrôle conforme'}
					</strong>
					<p>
						{invoice.ecart_commentaire ||
							(amountSummary.aligned
								? 'Les montants PFN et NET PAY sont alignés.'
								: `Écart de ${formatMoney(amountSummary.ecartAbs, dev)} entre PFN et NET PAY.`)}
					</p>
					<div className="report-detail-badges">
						<span>Facture #{invoice.id}</span>
						{ctx.dumId ? <span>DUM #{ctx.dumId}</span> : null}
						<span className={`rd-pill rd-pill--${ctx.statutControle || 'neutral'}`}>
							{ctx.statutControle || '—'}
						</span>
					</div>
				</div>
			</section>

			<div className="report-detail-kpis">
				<article className="report-kpi-card">
					<Shield size={20} className="report-kpi-icon blue" />
					<div>
						<p>Taux de confiance</p>
						<strong>{confidence != null ? `${confidence} %` : '—'}</strong>
					</div>
				</article>
				<article className="report-kpi-card">
					<AlertTriangle size={20} className="report-kpi-icon red" />
					<div>
						<p>Nombre d&apos;écarts</p>
						<strong className={issueCount > 0 ? 'is-negative' : ''}>
							{String(issueCount).padStart(2, '0')}
						</strong>
					</div>
				</article>
				<article className="report-kpi-card">
					<Clock size={20} className="report-kpi-icon slate" />
					<div>
						<p>Date de comparaison</p>
						<strong>
							{ctx.comparedAt
								? new Date(ctx.comparedAt).toLocaleString('fr-FR')
								: '—'}
						</strong>
					</div>
				</article>
			</div>

			<div className="report-detail-layout">
				<section className="report-detail-main">
					<div className="report-table-card-head">
						<h2>Détails de la comparaison</h2>
						<button type="button" className="rd-btn ghost small" onClick={handleExportPdf}>
							<Download size={14} />
							PDF
						</button>
					</div>
					<div className="report-table-wrap">
						<table className="report-detail-table">
							<thead>
								<tr>
									<th>Champ de données</th>
									<th>Valeur DUM</th>
									<th>Valeur facture</th>
									<th>Écart</th>
									<th>Statut</th>
								</tr>
							</thead>
							<tbody>
								{comparisonRows.map((row) => (
									<tr key={row.code} className={`row-${row.tone}`}>
										<td>{row.categorie}</td>
										<td>{row.dumValue}</td>
										<td>{row.factureValue}</td>
										<td>{row.ecart}</td>
										<td>
											<span className={`rd-status rd-status--${row.tone}`}>
												{row.tone === 'ok' ? (
													<CheckCircle2 size={14} />
												) : (
													<XCircle size={14} />
												)}
												{row.statut}
											</span>
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>

					<div className="report-detail-footnotes">
						<article>
							<h3>Synthèse montants</h3>
							<p>
								PFN DUM : <strong>{formatMoney(amountSummary.pfn, dev)}</strong>
							</p>
							<p>
								NET PAY : <strong>{formatMoney(amountSummary.netPay, dev)}</strong>
							</p>
						</article>
						<article>
							<h3>Pièces jointes consultées</h3>
							<ul>
								{ctx.attachments.map((a) => (
									<li key={a.name}>
										<FileText size={14} />
										<span>{a.label}</span> — {a.name}
									</li>
								))}
							</ul>
						</article>
					</div>
				</section>

				<aside className="report-detail-sidebar">
					<div className="report-sidebar-card">
						<h3>Actions dossier</h3>
						<button type="button" className="rd-btn primary block" onClick={openReconciliation}>
							Ouvrir la réconciliation
						</button>
						<Link
							to={ctx.dumId ? `/validation?documentId=${ctx.dumId}` : '/validation'}
							className="rd-btn outline block"
						>
							Corriger la DUM
						</Link>
						<Link
							to={`/invoice-validation?invoiceId=${ctx.invoiceId}`}
							className="rd-btn outline block"
						>
							Corriger la facture
						</Link>
						<button
							type="button"
							className="rd-btn outline block"
							onClick={handleExportPdf}
							disabled={exporting}
						>
							<Download size={16} />
							Télécharger PDF
						</button>
					</div>
					<div className="report-sidebar-card">
						<h3>Notes</h3>
						<p className="report-sidebar-note">
							{invoice.ecart_commentaire || 'Aucun commentaire enregistré.'}
						</p>
					</div>
					<div className="report-sidebar-progress">
						<p>Vérification enregistrée</p>
						<div className="report-progress-bar">
							<div
								className="report-progress-fill"
								style={{
									width: amountSummary.aligned && issueCount === 0 ? '100%' : '70%',
								}}
							/>
						</div>
					</div>
				</aside>
			</div>
		</div>
	);
}

export default ReportDetailPage;
