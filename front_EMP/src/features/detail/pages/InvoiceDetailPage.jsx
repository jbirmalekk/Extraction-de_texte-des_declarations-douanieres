import { useEffect, useMemo, useState } from 'react';
import {
	AlertTriangle,
	ArrowLeft,
	FileText,
	GitCompare,
	Receipt,
} from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import ErpExportButton from '@/features/erp/components/ErpExportButton';
import DetailSummaryHeader from '@/features/detail/components/DetailSummaryHeader';
import DetailDocumentPreview from '@/features/detail/components/DetailDocumentPreview';
import { useAuth } from '@/shared/hooks/useAuth';
import { ERP_EXPORT } from '@/shared/utils/erpExport';
import DetailFieldsPanel from '@/features/detail/components/DetailFieldsPanel';
import { fetchInvoiceById } from '@/shared/services/invoiceApi';
import { fetchDocumentDetail } from '@/shared/services/ocrService';
import {
	buildInvoiceDetailSections,
	formatControleTone,
	formatInvoiceStatut,
} from '@/shared/utils/detailDisplay';
import { beginReconciliationSession } from '@/shared/utils/crossVerificationSession';
import { hydrateInvoiceContextFromApi } from '@/shared/utils/documentContextStorage';
import {
	canShowReconciliation,
	isDumValidated,
	isInvoiceValidated,
	isReconciliationControlOk,
	isReconciliationNeedsRedo,
} from '@/shared/utils/workflowActions';

function InvoiceDetailPage() {
	const { invoiceId } = useParams();
	const navigate = useNavigate();
	const { user } = useAuth();
	const [invoice, setInvoice] = useState(null);
	const [linkedDumStatut, setLinkedDumStatut] = useState(null);
	const [activeTab, setActiveTab] = useState('fields');
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState('');
	const [openingValidation, setOpeningValidation] = useState(false);

	const invoiceSections = useMemo(() => buildInvoiceDetailSections(invoice), [invoice]);
	const statusInfo = formatInvoiceStatut(invoice?.statut);
	const controleInfo = formatControleTone(invoice?.statut_controle);
	const invoiceValidated = isInvoiceValidated(invoice?.statut);
	const reconOk = isReconciliationControlOk(invoice?.statut_controle);
	const reportInvoiceId = reconOk && invoice?.id ? invoice.id : null;
	const linkedPartnerValidated = invoice?.dum_document_id
		? isDumValidated(linkedDumStatut)
		: null;
	const showReconcile =
		isReconciliationNeedsRedo(invoice?.statut_controle) && invoiceValidated
			? true
			: canShowReconciliation({
					sourceValidated: invoiceValidated,
					linkedPartnerValidated,
					reconOk,
				});

	const createdLabel = invoice?.created_at
		? new Date(invoice.created_at).toLocaleString('fr-FR')
		: '—';
	const comparedLabel = invoice?.compared_at
		? new Date(invoice.compared_at).toLocaleString('fr-FR')
		: '—';

	useEffect(() => {
		let active = true;
		const load = async () => {
			setLoading(true);
			setError('');
			try {
				const data = await fetchInvoiceById(invoiceId);
				let dumStatut = null;
				if (data?.dum_document_id) {
					const dum = await fetchDocumentDetail(data.dum_document_id).catch(() => null);
					dumStatut = dum?.statut ?? null;
				}
				if (active) {
					setInvoice(data);
					setLinkedDumStatut(dumStatut);
				}
			} catch (err) {
				if (active) {
					setError(err?.response?.data?.detail || 'Impossible de charger cette facture.');
				}
			} finally {
				if (active) {
					setLoading(false);
				}
			}
		};
		load();
		return () => {
			active = false;
		};
	}, [invoiceId]);

	const openValidation = async () => {
		setOpeningValidation(true);
		try {
			await hydrateInvoiceContextFromApi(invoiceId);
			navigate('/invoice-validation', {
				state: { fromHistory: true, invoiceId: Number(invoiceId) },
			});
		} catch (err) {
			setError(err?.response?.data?.detail || 'Impossible d’ouvrir la validation pour cette facture.');
		} finally {
			setOpeningValidation(false);
		}
	};

	const handleReconciliation = () => {
		if (!invoice?.id) {
			return;
		}
		beginReconciliationSession({
			sourceType: 'invoice',
			sourceId: invoice.id,
			sourceNumero: invoice.numero_facture,
			sourceDate: invoice.date_facture,
			sourceLabel: invoice.numero_facture,
			sourceFileName: invoice.fichier_nom,
		});
		navigate('/cross-verification');
	};

	const warnings = Array.isArray(invoice?.extraction_warnings)
		? invoice.extraction_warnings
		: [];

	return (
		<section className="document-detail-page invoice-detail-page">
			<header className="detail-hero detail-hero--invoice">
				<div className="detail-hero-copy">
					<button type="button" className="text-link back-link" onClick={() => navigate(-1)}>
						<ArrowLeft size={16} /> Retour
					</button>
					<p className="hero-pill">Facture fournisseur</p>
					<h1>Détail facture</h1>
					<p className="subtitle detail-subtitle">
						Champs extraits, montants, logistique, contrôle DUM et lignes de facturation.
					</p>
				</div>
				<div className="detail-hero-actions detail-hero-actions--row">
					{!invoiceValidated ? (
						<button
							type="button"
							className="history-btn outline"
							onClick={openValidation}
							disabled={openingValidation}
						>
							{openingValidation ? 'Chargement…' : 'Validation facture'}
						</button>
					) : null}
					{reportInvoiceId ? (
						<>
							<Link to={`/reports/${reportInvoiceId}`} className="history-btn primary">
								Voir le rapport
							</Link>
							<ErpExportButton
								kind={ERP_EXPORT.DOSSIER}
								invoiceId={Number(invoiceId)}
								dumId={invoice?.dum_document_id}
								reference={invoice?.numero_facture}
								statutControle={invoice?.statut_controle}
								isAmountAligned={invoice?.statut_controle === 'ok'}
								isAdmin={user?.role === 'admin'}
							/>
						</>
					) : null}
					{invoiceValidated && !reportInvoiceId ? (
						<ErpExportButton
							kind={ERP_EXPORT.INVOICE}
							invoiceId={Number(invoiceId)}
							reference={invoice?.numero_facture}
						/>
					) : null}
					{showReconcile ? (
						<button type="button" className="history-btn primary" onClick={handleReconciliation}>
							<GitCompare size={16} />
							Réconciliation
						</button>
					) : null}
				</div>
			</header>

			{error ? (
				<div className="activities history-empty">
					<p>{error}</p>
				</div>
			) : null}

			{loading ? (
				<div className="activities history-empty">
					<p>Chargement…</p>
				</div>
			) : invoice ? (
				<div className="detail-shell">
					
					<section className="detail-summary card-panel detail-summary--invoice">
						<DetailSummaryHeader
							icon={Receipt}
							iconClassName="detail-doc-icon--invoice"
							fileLabel={invoice.fichier_nom || `Facture #${invoice.id}`}
							numero={invoice.numero_facture || 'N° facture non renseigné'}
							date={invoice.date_facture}
							metaLine={
								<>
									Statut <span className={`status-pill ${statusInfo.tone}`}>{statusInfo.label}</span>
									{' · '}Créée le <strong>{createdLabel}</strong>
								</>
							}
						/>
						<div className="detail-summary-grid">
							<div>
								<span>Client</span>
								<strong>{invoice.client_nom || '—'}</strong>
							</div>
							<div>
								<span>NET PAY</span>
								<strong>
									{invoice.net_pay != null
										? `${invoice.net_pay} ${invoice.devise || ''}`
										: '—'}
								</strong>
							</div>
							<div>
								<span>Montant TTC</span>
								<strong>
									{invoice.montant_ttc != null
										? `${invoice.montant_ttc} ${invoice.devise || ''}`
										: '—'}
								</strong>
							</div>
							<div>
								<span>DUM liée</span>
								<strong>
									{invoice.dum_document_id ? (
										<Link to={`/documents/${invoice.dum_document_id}`}>
											{invoice.numero_declaration_dum ||
												`DUM #${invoice.dum_document_id}`}
											{invoice.date_declaration_dum
												? ` · ${invoice.date_declaration_dum}`
												: ''}
										</Link>
									) : (
										'—'
									)}
								</strong>
							</div>
							<div>
								<span>Contrôle croisé</span>
								<strong>
									<span className={`history-recon-pill ${controleInfo.tone}`}>
										{controleInfo.label}
									</span>
								</strong>
							</div>
							<div>
								<span>Écart montant</span>
								<strong>{invoice.ecart_montant ?? '—'}</strong>
							</div>
							<div>
								<span>Dernière comparaison</span>
								<strong>{comparedLabel}</strong>
							</div>
							<div>
								<span>Incoterm / transport</span>
								<strong>
									{[invoice.incoterm, invoice.mode_transport_libelle]
										.filter(Boolean)
										.join(' · ') || '—'}
								</strong>
							</div>
						</div>
						{invoice.ecart_commentaire ? (
							<p className="detail-comment">{invoice.ecart_commentaire}</p>
						) : null}
					</section>

		

					<div className="detail-tabs">
						<button
							type="button"
							className={activeTab === 'fields' ? 'detail-tab active' : 'detail-tab'}
							onClick={() => setActiveTab('fields')}
						>
							<FileText size={16} />
							Tous les champs
						</button>
						<button
							type="button"
							className={activeTab === 'lines' ? 'detail-tab active' : 'detail-tab'}
							onClick={() => setActiveTab('lines')}
						>
							Lignes ({invoice.lines?.length || 0})
						</button>
						{invoice.controle_anomalies?.length ? (
							<button
								type="button"
								className={activeTab === 'anomalies' ? 'detail-tab active' : 'detail-tab'}
								onClick={() => setActiveTab('anomalies')}
							>
								Anomalies ({invoice.controle_anomalies.length})
							</button>
						) : null}
					</div>

					{activeTab === 'fields' ? (
						<DetailFieldsPanel
							sections={invoiceSections.filter((s) => s.section !== 'Lignes facture (détail)')}
							title="Champs extraits (facture)"
						/>
					) : null}

					{activeTab === 'lines' ? (
						<section className="card-panel detail-fields-panel">
							<h2>Lignes de facture</h2>
							{invoice.lines?.length ? (
								<div className="invoice-lines-table-wrap">
									<table className="invoice-lines-table">
										<thead>
											<tr>
												<th>#</th>
												<th>Référence</th>
												<th>Désignation</th>
												<th>Qté</th>
												<th>Prix unit.</th>
												<th>Montant</th>
												<th>Devise</th>
											</tr>
										</thead>
										<tbody>
											{invoice.lines.map((line) => (
												<tr key={line.id ?? line.line_order}>
													<td>{line.line_order}</td>
													<td>{line.reference || '—'}</td>
													<td>{line.designation || '—'}</td>
													<td>{line.quantite ?? '—'}</td>
													<td>{line.prix_unitaire ?? '—'}</td>
													<td>{line.montant_ligne ?? '—'}</td>
													<td>{line.devise_ligne || '—'}</td>
												</tr>
											))}
										</tbody>
									</table>
								</div>
							) : (
								<p className="detail-empty-tab">Aucune ligne enregistrée.</p>
							)}
						</section>
					) : null}

					{activeTab === 'anomalies' && invoice.controle_anomalies?.length ? (
						<section className="card-panel detail-fields-panel">
							<h2>Résultat du dernier contrôle DUM</h2>
							<div className="invoice-lines-table-wrap">
								<table className="invoice-lines-table">
									<thead>
										<tr>
											<th>Code</th>
											<th>Message</th>
											<th>Valeur DUM</th>
											<th>Valeur facture</th>
										</tr>
									</thead>
									<tbody>
										{invoice.controle_anomalies.map((a) => (
											<tr key={a.code}>
												<td>{a.code}</td>
												<td>{a.message}</td>
												<td>{a.dum_value ?? '—'}</td>
												<td>{a.facture_value ?? '—'}</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
						</section>
					) : null}

					{invoice.storage?.nextcloud_url ? (
						<section className="card-panel detail-meta-card">
							<h2>Stockage GED</h2>
							<p>
								<a href={invoice.storage.nextcloud_url} target="_blank" rel="noreferrer">
									{invoice.storage.nextcloud_path || invoice.dossier || 'Ouvrir dans Nextcloud'}
								</a>
							</p>
						</section>
					) : null}
				</div>
			) : null}
		</section>
	);
}

export default InvoiceDetailPage;
