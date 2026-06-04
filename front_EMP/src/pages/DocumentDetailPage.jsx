import { useEffect, useMemo, useState } from 'react';
import {
	ArrowLeft,
	FileText,
	GitCompare,
	Package,
	Receipt,
	ShieldCheck,
} from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import ErpExportButton from '../components/Erp/ErpExportButton';
import DetailDocumentPreview from '../components/Detail/DetailDocumentPreview';
import { ERP_EXPORT } from '../utils/erpExport';
import DetailFieldsPanel from '../components/Detail/DetailFieldsPanel';
import { fetchInvoiceByDumId } from '../services/invoiceApi';
import { fetchDocumentCorrections, fetchDocumentDetail } from '../services/ocrService';
import { buildDumDetailSections, formatDumStatut } from '../utils/detailDisplay';
import { beginReconciliationSession } from '../utils/crossVerificationSession';
import { hydrateDumContextFromApi } from '../utils/documentContextStorage';
import { isDumValidated, isReconciliationControlOk } from '../utils/workflowActions';

function DocumentDetailPage() {
	const { documentId } = useParams();
	const navigate = useNavigate();
	const [document, setDocument] = useState(null);
	const [linkedInvoice, setLinkedInvoice] = useState(null);
	const [corrections, setCorrections] = useState([]);
	const [activeTab, setActiveTab] = useState('fields');
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState('');
	const [openingValidation, setOpeningValidation] = useState(false);

	const dumSections = useMemo(() => buildDumDetailSections(document), [document]);
	const statusInfo = formatDumStatut(document?.statut);
	const dumValidated = isDumValidated(document?.statut);
	const reconOk = isReconciliationControlOk(linkedInvoice?.statut_controle);
	const reportInvoiceId = linkedInvoice?.id && reconOk ? linkedInvoice.id : null;
	const showReconcile = !reconOk;
	const createdLabel = document?.created_at
		? new Date(document.created_at).toLocaleString('fr-FR')
		: '—';

	useEffect(() => {
		let isActive = true;

		const loadDocument = async () => {
			setLoading(true);
			setError('');
			try {
				const [data, corrPayload, invLink] = await Promise.all([
					fetchDocumentDetail(documentId),
					fetchDocumentCorrections(documentId).catch(() => ({ corrections: [] })),
					fetchInvoiceByDumId(documentId).catch(() => null),
				]);
				if (isActive) {
					setDocument(data);
					setCorrections(corrPayload?.corrections || []);
					setLinkedInvoice(invLink);
				}
			} catch (fetchError) {
				if (isActive) {
					setError(fetchError?.response?.data?.detail || 'Impossible de charger ce document.');
				}
			} finally {
				if (isActive) {
					setLoading(false);
				}
			}
		};

		loadDocument();

		return () => {
			isActive = false;
		};
	}, [documentId]);

	const openValidation = async () => {
		setOpeningValidation(true);
		try {
			await hydrateDumContextFromApi(documentId);
			navigate('/validation', { state: { fromHistory: true, documentId: Number(documentId) } });
		} catch (fetchError) {
			setError(fetchError?.response?.data?.detail || 'Impossible d’ouvrir la validation pour ce document.');
		} finally {
			setOpeningValidation(false);
		}
	};

	const handleReconciliation = () => {
		beginReconciliationSession({
			sourceType: 'dum',
			sourceId: Number(documentId),
			sourceNumero: document?.numero_declaration,
			sourceDate: document?.date_declaration,
			sourceLabel: document?.numero_declaration,
			sourceFileName: document?.fichier,
		});
		navigate('/cross-verification');
	};

	return (
		<section className="document-detail-page document-detail-page--dum">
			<header className="detail-hero detail-hero--dum">
				<div className="detail-hero-copy">
					<button type="button" className="text-link back-link" onClick={() => navigate(-1)}>
						<ArrowLeft size={16} /> Retour
					</button>
					<p className="hero-pill">Déclaration DUM</p>
					<h1>Détail DUM</h1>
					<p className="subtitle detail-subtitle">
						Consultation complète des champs extraits par OCR, articles, taxes et corrections.
					</p>
				</div>
				<div className="detail-hero-actions detail-hero-actions--row">
					{!dumValidated ? (
						<button
							type="button"
							className="history-btn outline"
							onClick={openValidation}
							disabled={openingValidation}
						>
							{openingValidation ? 'Chargement…' : 'Validation DUM'}
						</button>
					) : null}
					{reportInvoiceId ? (
						<>
							<Link to={`/reports/${reportInvoiceId}`} className="history-btn primary">
								Voir le rapport
							</Link>
							<ErpExportButton
								kind={ERP_EXPORT.DOSSIER}
								invoiceId={reportInvoiceId}
								dumId={Number(documentId)}
								reference={document?.numero_declaration}
								statutControle={linkedInvoice?.statut_controle}
								isAmountAligned={linkedInvoice?.statut_controle === 'ok'}
							/>
						</>
					) : null}
					{dumValidated && !reportInvoiceId ? (
						<ErpExportButton
							kind={ERP_EXPORT.DUM}
							dumId={Number(documentId)}
							reference={document?.numero_declaration}
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
			) : document ? (
				<div className="detail-shell">
					<DetailDocumentPreview
						kind="dum"
						documentId={documentId}
						fileName={document.fichier}
						contentType="application/pdf"
						dossier={document.dossier}
						title="Aperçu du document DUM"
					/>
					<section className="detail-summary card-panel detail-summary--dum">
						<div className="detail-summary-title">
							<div className="detail-doc-icon detail-doc-icon--dum">
								<FileText size={22} />
							</div>
							<div>
								<p className="stat-label">{document.fichier || `Document #${document.id}`}</p>
								<h2>{document.numero_declaration || 'N° déclaration non renseigné'}</h2>
								<p className="detail-summary-note">
									Propriétaire :{' '}
									<strong>{document.uploaded_by?.username || '—'}</strong> · Créé le{' '}
									<strong>{createdLabel}</strong>
								</p>
							</div>
						</div>
						<div className="detail-summary-grid">
							<div>
								<span>Statut traitement</span>
								<strong>
									<span className={`status-pill ${statusInfo.tone}`}>{statusInfo.label}</span>
								</strong>
							</div>
							<div>
								<span>Score OCR</span>
								<strong>{document.score_confiance ?? '—'}%</strong>
							</div>
							<div>
								<span>Qualité OCR</span>
								<strong>{document.qualite || '—'}</strong>
							</div>
							<div>
								<span>PFN / Montant PTFN</span>
								<strong>
									{document.montant_ptfn || '—'} {document.devise || ''}
								</strong>
							</div>
							<div>
								<span>Poids net</span>
								<strong>{document.poids_net ? `${document.poids_net} kg` : '—'}</strong>
							</div>
							<div>
								<span>Facture liée</span>
								<strong>
									{linkedInvoice?.id ? (
										<Link to={`/invoices/${linkedInvoice.id}`}>
											{linkedInvoice.numero_facture || `Facture #${linkedInvoice.id}`}
										</Link>
									) : (
										'—'
									)}
								</strong>
							</div>
						</div>
					</section>

					<div className="detail-tabs">
						<button
							type="button"
							className={activeTab === 'fields' ? 'detail-tab active' : 'detail-tab'}
							onClick={() => setActiveTab('fields')}
						>
							Champs extraits ({dumSections.reduce((n, s) => n + s.fields.length, 0)})
						</button>
						<button
							type="button"
							className={activeTab === 'lists' ? 'detail-tab active' : 'detail-tab'}
							onClick={() => setActiveTab('lists')}
						>
							Articles & taxes
						</button>
						<button
							type="button"
							className={activeTab === 'corrections' ? 'detail-tab active' : 'detail-tab'}
							onClick={() => setActiveTab('corrections')}
						>
							Corrections ({corrections.length})
						</button>
					</div>

					{activeTab === 'fields' ? (
						<DetailFieldsPanel
							sections={dumSections}
							title="Tous les champs extraits (DUM)"
						/>
					) : null}

					{activeTab === 'lists' ? (
						<>
							<section className="card-panel detail-fields-panel">
								<h2>
									<Package size={18} /> Articles ({document.articles?.length || 0})
								</h2>
								{document.articles?.length ? (
									<div className="invoice-lines-table-wrap">
										<table className="invoice-lines-table">
											<thead>
												<tr>
													<th>Ligne</th>
													<th>Code HS</th>
													<th>Désignation</th>
													<th>Qté</th>
													<th>Total</th>
												</tr>
											</thead>
											<tbody>
												{document.articles.map((a) => (
													<tr key={a.id ?? a.num_ligne}>
														<td>{a.num_ligne ?? '—'}</td>
														<td>{a.code_hs || '—'}</td>
														<td>{a.designation || '—'}</td>
														<td>{a.quantite ?? '—'}</td>
														<td>{a.total_ligne ?? '—'}</td>
													</tr>
												))}
											</tbody>
										</table>
									</div>
								) : (
									<p className="detail-empty-tab">Aucun article enregistré.</p>
								)}
							</section>
							<section className="card-panel detail-fields-panel">
								<h2>
									<ShieldCheck size={18} /> Taxes ({document.taxes?.length || 0})
								</h2>
								{document.taxes?.length ? (
									<div className="invoice-lines-table-wrap">
										<table className="invoice-lines-table">
											<thead>
												<tr>
													<th>Code</th>
													<th>Assiette</th>
													<th>Quotité</th>
													<th>Montant</th>
												</tr>
											</thead>
											<tbody>
												{document.taxes.map((t) => (
													<tr key={t.id}>
														<td>{t.code || '—'}</td>
														<td>{t.assiette || '—'}</td>
														<td>{t.quotite || '—'}</td>
														<td>{t.montant || '—'}</td>
													</tr>
												))}
											</tbody>
										</table>
									</div>
								) : (
									<p className="detail-empty-tab">Aucune taxe enregistrée.</p>
								)}
							</section>
						</>
					) : null}

					{activeTab === 'corrections' ? (
						<section className="card-panel detail-fields-panel">
							<h2>Historique des corrections</h2>
							{corrections.length === 0 ? (
								<p className="detail-empty-tab">Aucune correction enregistrée.</p>
							) : (
								<ul className="corrections-timeline">
									{corrections.map((c) => (
										<li key={c.id} className="corrections-timeline-item">
											<div className="corrections-timeline-head">
												<strong>{c.field_key || 'Champ'}</strong>
												<span>
													{c.modified_at
														? new Date(c.modified_at).toLocaleString('fr-FR')
														: '—'}
													{c.modified_by_username
														? ` · ${c.modified_by_username}`
														: ''}
												</span>
											</div>
											<p>
												<span className="corr-old">{c.old_value ?? '—'}</span>
												{' → '}
												<span className="corr-new">{c.new_value ?? '—'}</span>
											</p>
										</li>
									))}
								</ul>
							)}
						</section>
					) : null}

					{linkedInvoice ? (
						<section className="card-panel detail-linked-card">
							<h2>
								<Receipt size={18} /> Facture partenaire liée
							</h2>
							<p>
								<Link to={`/invoices/${linkedInvoice.id}`}>
									{linkedInvoice.numero_facture || `Facture #${linkedInvoice.id}`}
								</Link>
								{linkedInvoice.net_pay != null
									? ` — NET PAY ${linkedInvoice.net_pay} ${linkedInvoice.devise || ''}`
									: ''}
							</p>
						</section>
					) : null}
				</div>
			) : null}
		</section>
	);
}

export default DocumentDetailPage;
