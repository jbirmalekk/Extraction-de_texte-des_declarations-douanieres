import { useCallback, useEffect, useMemo, useState } from 'react';
import {
	AlertTriangle,
	ArrowLeft,
	CheckCircle2,
	ChevronRight,
	FileText,
	FileUp,
	Download,
	GitCompare,
	RefreshCw,
	XCircle,
} from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import WorkflowBreadcrumb from '../components/Workflow/WorkflowBreadcrumb';
import { useAuth } from '../hooks/useAuth';
import {
	compareInvoiceWithDum,
	fetchInvoiceById,
	fetchInvoicesList,
	linkInvoiceToDum,
} from '../services/invoiceApi';
import { fetchDocumentDetail, fetchOcrDocuments } from '../services/ocrService';
import DocumentPreviewPanel from '../components/CrossVerify/DocumentPreviewPanel';
import ErpExportButton from '../components/Erp/ErpExportButton';
import { ERP_EXPORT } from '../utils/erpExport';
import {
	buildComparisonRows,
	formatMoney,
	getMontantAlignmentSummary,
	isMontantAligned,
} from '../utils/compareDisplay';
import { exportComparisonReportPdf } from '../utils/reconciliationReportPdf';
import { countComparisonIssues } from '../utils/reportContext';
import { buildReconciliationPairRef } from '../utils/crossVerifyDisplay';
import { loadCrossVerifyPreviews } from '../utils/compareDocumentPreview';
import {
	buildLinkedDumSuffix,
	buildLinkedInvoiceSuffix,
	indexDumDocsById,
	resolveSourceRegisteredLine,
} from '../utils/crossVerifyDisplay';
import {
	clearCrossVerificationSession,
	getCrossVerificationSession,
	saveCrossVerificationSession,
	updateCrossVerificationSession,
} from '../utils/crossVerificationSession';
import { buildInvoiceByDumMap } from '../utils/historyUnified';
import {
	assertReconciliationPairReady,
	isDumValidated,
	isInvoiceValidated,
	RECONCILIATION_BLOCKED_MSG,
} from '../utils/workflowActions';
import './CrossVerificationPage.css';
import '../components/Workflow/WorkflowBreadcrumb.css';

function CrossVerificationPage() {
	const navigate = useNavigate();
	const location = useLocation();
	const { user } = useAuth();
	const [session, setSession] = useState(() => getCrossVerificationSession());
	const [phase, setPhase] = useState('select');
	const [dumDocs, setDumDocs] = useState([]);
	const [invoices, setInvoices] = useState([]);
	const [partnerId, setPartnerId] = useState('');
	const [loadingLists, setLoadingLists] = useState(true);
	const [isWorking, setIsWorking] = useState(false);
	const [error, setError] = useState('');
	const [comparison, setComparison] = useState(null);
	const [dumDetail, setDumDetail] = useState(null);
	const [invoiceDetail, setInvoiceDetail] = useState(null);
	const [dumPreview, setDumPreview] = useState(null);
	const [invoicePreview, setInvoicePreview] = useState(null);
	const [previewsLoading, setPreviewsLoading] = useState(false);
	const [previewErrors, setPreviewErrors] = useState({ dum: '', invoice: '' });
	const [hubDumId, setHubDumId] = useState('');
	const [hubInvoiceId, setHubInvoiceId] = useState('');

	const isHubMode = !session?.sourceType || !session?.sourceId;
	const sourceType = session?.sourceType;
	const sourceId = session?.sourceId;
	const invoiceId =
		sourceType === 'invoice' ? Number(sourceId) : Number(partnerId || session?.partnerId);
	const dumId =
		sourceType === 'dum' ? Number(sourceId) : Number(partnerId || session?.partnerId);

	const partnerKind = sourceType === 'dum' ? 'invoice' : 'dum';

	const loadLists = useCallback(async () => {
		setLoadingLists(true);
		setError('');
		try {
			const [docs, invPage] = await Promise.all([
				fetchOcrDocuments({ limit: 80 }),
				fetchInvoicesList({ limit: 80 }, user).catch(() => ({ items: [] })),
			]);
			setDumDocs(Array.isArray(docs) ? docs : []);
			setInvoices(invPage?.items ?? []);
		} catch (err) {
			setError(
				err?.response?.data?.detail ||
					'Impossible de charger la liste des documents pour la comparaison.'
			);
		} finally {
			setLoadingLists(false);
		}
	}, [user]);

	useEffect(() => {
		loadLists();
	}, [loadLists]);

	const hydrateDocumentPreviews = useCallback(
		async (dumDocId, invId, sess = session, dumDoc = dumDetail, inv = invoiceDetail) => {
			if (!dumDocId || !invId) {
				return;
			}
			setPreviewsLoading(true);
			setPreviewErrors({ dum: '', invoice: '' });
			try {
				const {
					dumPreview: dumPrev,
					invoicePreview: invPrev,
					errors: previewLoadErrors,
				} = await loadCrossVerifyPreviews({
					dumId: dumDocId,
					invoiceId: invId,
					session: sess,
					dumDoc,
					invoice: inv,
				});
				setDumPreview(dumPrev);
				setInvoicePreview(invPrev);
				setPreviewErrors(previewLoadErrors);
				try {
					updateCrossVerificationSession({
						dumPreview: dumPrev,
						invoicePreview: invPrev,
					});
				} catch {
					// Quota localStorage — les aperçus restent en mémoire pour la session courante
				}
			} catch {
				setPreviewErrors({
					dum: 'Erreur lors du chargement de l\u2019aperçu DUM.',
					invoice: 'Erreur lors du chargement de l\u2019aperçu facture.',
				});
			} finally {
				setPreviewsLoading(false);
			}
		},
		[session]
	);

	/** Ouverture depuis Rapports → « Ouvrir la réconciliation » (bonne facture / DUM). */
	useEffect(() => {
		const openReport = Boolean(location.state?.openReport);
		const invId = Number(location.state?.invoiceId);
		const dId = Number(location.state?.dumId);
		if (!openReport || !Number.isFinite(invId) || invId <= 0 || !Number.isFinite(dId) || dId <= 0) {
			return undefined;
		}

		let cancelled = false;

		(async () => {
			setIsWorking(true);
			setError('');
			try {
				const nextSession = saveCrossVerificationSession({
					sourceType: 'invoice',
					sourceId: invId,
					partnerType: 'dum',
					partnerId: dId,
					invoiceId: invId,
					dumDocumentId: dId,
				});
				if (cancelled) {
					return;
				}
				setSession(nextSession);
				setPartnerId(String(dId));

				const [invDetail, dumDoc] = await Promise.all([
					fetchInvoiceById(invId),
					fetchDocumentDetail(dId).catch(() => null),
				]);
				if (cancelled) {
					return;
				}
				setComparison(invDetail);
				setInvoiceDetail(invDetail);
				setDumDetail(dumDoc);
				setPhase('compare');
				updateCrossVerificationSession({
					comparisonResult: invDetail,
					partnerId: dId,
				});
				await hydrateDocumentPreviews(dId, invId, nextSession, dumDoc, invDetail);
			} catch (err) {
				if (!cancelled) {
					setError(
						typeof err?.response?.data?.detail === 'string'
							? err.response.data.detail
							: 'Impossible de rouvrir ce contrôle.'
					);
				}
			} finally {
				if (!cancelled) {
					setIsWorking(false);
				}
			}
		})();

		return () => {
			cancelled = true;
		};
	}, [
		location.key,
		location.state?.openReport,
		location.state?.invoiceId,
		location.state?.dumId,
		hydrateDocumentPreviews,
	]);

	useEffect(() => {
		if (session?.pendingPartnerId) {
			setPartnerId(String(session.pendingPartnerId));
			const next = updateCrossVerificationSession({ pendingPartnerId: null });
			setSession(next);
		}
	}, [session?.pendingPartnerId]);

	useEffect(() => {
		if (session?.redoReconciliation) {
			setPhase('select');
			setPartnerId('');
			setComparison(null);
			setDumPreview(null);
			setInvoicePreview(null);
			return undefined;
		}
		if (!session?.partnerId || !session?.comparisonResult) {
			return undefined;
		}

		setPartnerId(String(session.partnerId));
		setComparison(session.comparisonResult);
		setPhase('compare');

		const inv =
			session.sourceType === 'invoice'
				? Number(session.sourceId)
				: Number(session.partnerId);
		const dum =
			session.sourceType === 'dum' ? Number(session.sourceId) : Number(session.partnerId);

		if (!inv || !dum) {
			return undefined;
		}

		let cancelled = false;

		(async () => {
			const [invDetail, dumDoc] = await Promise.all([
				fetchInvoiceById(inv).catch(() => null),
				fetchDocumentDetail(dum).catch(() => null),
			]);
			if (cancelled) {
				return;
			}
			if (invDetail) {
				setInvoiceDetail(invDetail);
			}
			if (dumDoc) {
				setDumDetail(dumDoc);
			}
			await hydrateDocumentPreviews(dum, inv, session, dumDoc, invDetail);
		})();

		return () => {
			cancelled = true;
		};
	}, [
		session?.redoReconciliation,
		session?.partnerId,
		session?.comparisonResult,
		session?.sourceType,
		session?.sourceId,
	]);

	const dumById = useMemo(() => indexDumDocsById(dumDocs), [dumDocs]);
	const invoiceByDumId = useMemo(() => buildInvoiceByDumMap(invoices), [invoices]);

	const sourceRegisteredLine = useMemo(
		() =>
			resolveSourceRegisteredLine({
				sourceType,
				sourceId,
				session,
				dumDocs,
				invoices,
			}),
		[sourceType, sourceId, session, dumDocs, invoices]
	);

	const sourceValidationMessage = useMemo(() => {
		if (!sourceType || !sourceId) {
			return '';
		}
		if (sourceType === 'dum') {
			const src = dumDocs.find((d) => Number(d.id) === Number(sourceId));
			if (src && !isDumValidated(src.statut)) {
				return 'Validez cette DUM (étape Validation) avant de lancer la réconciliation.';
			}
			return '';
		}
		const src = invoices.find((inv) => Number(inv.id) === Number(sourceId));
		if (src && !isInvoiceValidated(src.statut)) {
			return 'Validez cette facture (étape Validation) avant de lancer la réconciliation.';
		}
		return '';
	}, [sourceType, sourceId, dumDocs, invoices]);

	const formatListDate = useCallback((value) => {
		const raw = String(value ?? '').trim();
		return raw || null;
	}, []);

	const validatedDumOptions = useMemo(
		() =>
			dumDocs
				.filter((doc) => isDumValidated(doc.statut))
				.map((doc) => {
					const numero = doc.numero_declaration?.trim() || null;
					const date = formatListDate(doc.date_declaration);
					return {
						id: doc.id,
						label: numero ? `N° ${numero}` : `DUM #${doc.id}`,
						sub: date ? `Date ${date}` : 'Date —',
					};
				}),
		[dumDocs, formatListDate]
	);

	const validatedInvoiceOptions = useMemo(
		() =>
			invoices
				.filter((inv) => isInvoiceValidated(inv.statut))
				.map((inv) => {
					const numero = inv.numero_facture?.trim() || null;
					const date = formatListDate(inv.date_facture);
					return {
						id: inv.id,
						label: numero ? `N° ${numero}` : `Facture #${inv.id}`,
						sub: date ? `Date ${date}` : 'Date —',
					};
				}),
		[invoices, formatListDate]
	);

	const partnerOptions = useMemo(() => {
		if (partnerKind === 'invoice') {
			return invoices
				.filter((inv) => inv.id !== sourceId && isInvoiceValidated(inv.statut))
				.map((inv) => {
					const numero = inv.numero_facture?.trim() || null;
					const date = formatListDate(inv.date_facture);
					const linkedDum = inv.dum_document_id
						? dumById.get(Number(inv.dum_document_id))
						: null;
					const linkedSuffix = buildLinkedDumSuffix(
						linkedDum,
						inv.numero_declaration_dum
					);
					return {
						id: inv.id,
						label: numero ? `N° facture ${numero}` : `Facture #${inv.id}`,
						sub: date ? `Date facture ${date}` : 'Date facture —',
						linkedSuffix,
					};
				});
		}
		return dumDocs
			.filter((doc) => doc.id !== sourceId && isDumValidated(doc.statut))
			.map((doc) => {
				const numero = doc.numero_declaration?.trim() || null;
				const date = formatListDate(doc.date_declaration);
				return {
					id: doc.id,
					label: numero ? `N° déclaration ${numero}` : `DUM #${doc.id}`,
					sub: date ? `Date déclaration ${date}` : 'Date déclaration —',
					linkedSuffix: '',
				};
			});
	}, [partnerKind, invoices, dumDocs, sourceId, dumById, formatListDate]);

	const executeComparison = useCallback(
		async ({
			compareInvoiceId,
			compareDumId,
			selectedPartnerId,
			activeSession,
			partnerType,
		}) => {
			if (!compareInvoiceId || !compareDumId) {
				setError('Sélectionnez une DUM et une facture validées.');
				return;
			}

			const invRow =
				invoices.find((inv) => Number(inv.id) === Number(compareInvoiceId)) || invoiceDetail;
			const dumRow =
				dumDocs.find((doc) => Number(doc.id) === Number(compareDumId)) || dumDetail;
			const pairCheck = assertReconciliationPairReady({
				dumStatut: dumRow?.statut,
				invoiceStatut: invRow?.statut,
			});
			if (!pairCheck.ok) {
				setError(pairCheck.message || RECONCILIATION_BLOCKED_MSG);
				return;
			}

			setIsWorking(true);
			setError('');
			try {
				await linkInvoiceToDum(compareInvoiceId, { dum_document_id: compareDumId });
				const result = await compareInvoiceWithDum(compareInvoiceId, {
					dum_document_id: compareDumId,
				});
				setComparison(result);

				const [invDetail, dumDoc] = await Promise.all([
					fetchInvoiceById(compareInvoiceId),
					fetchDocumentDetail(compareDumId).catch(() => null),
				]);
				setInvoiceDetail(invDetail);
				setDumDetail(dumDoc);

				const {
					dumPreview: dumPrev,
					invoicePreview: invPrev,
					errors: previewLoadErrors,
				} = await loadCrossVerifyPreviews({
					dumId: compareDumId,
					invoiceId: compareInvoiceId,
					session: activeSession,
					dumDoc,
					invoice: invDetail,
				});
				setDumPreview(dumPrev);
				setInvoicePreview(invPrev);
				setPreviewErrors(previewLoadErrors);

				const nextSession = updateCrossVerificationSession({
					sourceType: activeSession?.sourceType || 'invoice',
					sourceId: activeSession?.sourceId || compareInvoiceId,
					sourceNumero:
						activeSession?.sourceNumero || invRow?.numero_facture || null,
					sourceLabel:
						activeSession?.sourceLabel || invRow?.numero_facture || null,
					partnerType: partnerType || 'dum',
					partnerId: selectedPartnerId ?? compareDumId,
					invoiceId: compareInvoiceId,
					dumDocumentId: compareDumId,
					comparisonResult: result,
					dumPreview: dumPrev,
					invoicePreview: invPrev,
					redoReconciliation: false,
				});
				setSession(nextSession);
				setPhase('compare');
			} catch (err) {
				const detail = err?.response?.data?.detail;
				setError(typeof detail === 'string' ? detail : 'Échec de la comparaison. Réessayez.');
			} finally {
				setIsWorking(false);
			}
		},
		[dumDocs, invoices, dumDetail, invoiceDetail]
	);

	const runComparison = async (selectedPartnerId) => {
		if (!invoiceId || !dumId) {
			setError('Sélectionnez un document partenaire valide.');
			return;
		}

		if (sourceValidationMessage) {
			setError(sourceValidationMessage);
			return;
		}

		await executeComparison({
			compareInvoiceId: invoiceId,
			compareDumId: dumId,
			selectedPartnerId,
			activeSession: session,
			partnerType: partnerKind,
		});
	};

	const handleHubStartReconciliation = async () => {
		const compareDumId = Number(hubDumId);
		const compareInvoiceId = Number(hubInvoiceId);
		if (!Number.isFinite(compareDumId) || compareDumId <= 0) {
			setError('Choisissez une DUM validée dans la liste.');
			return;
		}
		if (!Number.isFinite(compareInvoiceId) || compareInvoiceId <= 0) {
			setError('Choisissez une facture validée dans la liste.');
			return;
		}

		const invRow = invoices.find((inv) => Number(inv.id) === compareInvoiceId);
		const dumRow = dumDocs.find((doc) => Number(doc.id) === compareDumId);

		const initialSession = saveCrossVerificationSession({
			sourceType: 'invoice',
			sourceId: compareInvoiceId,
			sourceNumero: invRow?.numero_facture ?? null,
			sourceDate: invRow?.date_facture ?? null,
			sourceLabel: invRow?.numero_facture ?? null,
			sourceFileName: invRow?.fichier_nom || `Facture #${compareInvoiceId}`,
			partnerType: 'dum',
			partnerId: compareDumId,
			invoiceId: compareInvoiceId,
			dumDocumentId: compareDumId,
			redoReconciliation: false,
		});
		setSession(initialSession);

		await executeComparison({
			compareInvoiceId,
			compareDumId,
			selectedPartnerId: compareDumId,
			activeSession: initialSession,
			partnerType: 'dum',
		});
	};

	const handleStartCompare = () => {
		const id = Number(partnerId);
		if (!Number.isFinite(id) || id <= 0) {
			setError('Choisissez le document avec lequel effectuer la vérification croisée.');
			return;
		}
		runComparison(id);
	};

	const handleRecompare = () => {
		const pid = session?.partnerId || partnerId;
		if (pid) {
			runComparison(Number(pid));
		}
	};

	const comparisonRows = useMemo(
		() => buildComparisonRows(comparison, dumDetail, invoiceDetail),
		[comparison, dumDetail, invoiceDetail]
	);

	const amountSummary = useMemo(
		() => getMontantAlignmentSummary(comparison, dumDetail, invoiceDetail),
		[comparison, dumDetail, invoiceDetail]
	);
	const totalDum = amountSummary.pfn ?? comparison?.montant_declare_dum;
	const totalFacture = amountSummary.netPay ?? comparison?.net_pay ?? comparison?.montant_ttc;
	const ecart =
		amountSummary.ecartAbs != null ? amountSummary.ecartAbs : comparison?.ecart_montant;
	const devise = amountSummary.devise || '';
	const isAmountAligned = amountSummary.aligned;
	const isFullyAligned =
		comparison?.statut_controle === 'ok' && isAmountAligned;

	if (isHubMode) {
		const hubListsEmpty =
			!loadingLists &&
			validatedDumOptions.length === 0 &&
			validatedInvoiceOptions.length === 0;

		return (
			<div className="cross-verify-page fade-up">
				<header className="cross-verify-header">
					<div>
						<p className="cross-verify-kicker">Contrôle douanier</p>
						<h1>Contrôle DUM — Facture</h1>
						<p className="cross-verify-sub">
							Sélectionnez une DUM et une facture <strong>validées</strong>, puis lancez la
							comparaison des montants et références.
						</p>
					</div>
				</header>

				{error ? (
					<div className="cross-verify-alert error">
						<AlertTriangle size={18} />
						<span>{error}</span>
					</div>
				) : null}

				<section className="cross-verify-card cross-verify-hub">
					<h2>Rapprochement du dossier</h2>
					<p className="cross-verify-help">
						Seuls les documents ayant terminé l&apos;étape Validation apparaissent dans les listes.
					</p>

					{loadingLists ? (
						<p className="cross-verify-help">Chargement des documents…</p>
					) : (
						<div className="cross-verify-hub-grid">
							<div className="cross-verify-hub-field">
								<label className="cross-verify-select-label" htmlFor="hub-dum">
									DUM validée
								</label>
								<p className="cross-verify-select-hint">N° déclaration · date</p>
								<select
									id="hub-dum"
									className="cross-verify-select"
									value={hubDumId}
									onChange={(e) => setHubDumId(e.target.value)}
									disabled={isWorking}
								>
									<option value="">— Choisir une DUM —</option>
									{validatedDumOptions.map((opt) => (
										<option key={opt.id} value={opt.id}>
											{opt.label} · {opt.sub}
										</option>
									))}
								</select>
								{!loadingLists && validatedDumOptions.length === 0 ? (
									<p className="cross-verify-help cross-verify-help--warn">
										Aucune DUM validée. Validez une DUM depuis Résultats DUM ou l&apos;historique.
									</p>
								) : null}
							</div>

							<div className="cross-verify-hub-field">
								<label className="cross-verify-select-label" htmlFor="hub-invoice">
									Facture validée
								</label>
								<p className="cross-verify-select-hint">N° facture · date</p>
								<select
									id="hub-invoice"
									className="cross-verify-select"
									value={hubInvoiceId}
									onChange={(e) => setHubInvoiceId(e.target.value)}
									disabled={isWorking}
								>
									<option value="">— Choisir une facture —</option>
									{validatedInvoiceOptions.map((opt) => (
										<option key={opt.id} value={opt.id}>
											{opt.label} · {opt.sub}
										</option>
									))}
								</select>
								{!loadingLists && validatedInvoiceOptions.length === 0 ? (
									<p className="cross-verify-help cross-verify-help--warn">
										Aucune facture validée. Validez une facture depuis Résultats facture ou
										l&apos;historique.
									</p>
								) : null}
							</div>
						</div>
					)}

					<div className="cross-verify-actions cross-verify-actions--hub">
						<button
							type="button"
							className="cross-verify-btn ghost"
							onClick={loadLists}
							disabled={loadingLists || isWorking}
						>
							<RefreshCw size={16} />
							Actualiser
						</button>
						<button
							type="button"
							className="cross-verify-btn primary"
							onClick={handleHubStartReconciliation}
							disabled={
								!hubDumId ||
								!hubInvoiceId ||
								loadingLists ||
								isWorking ||
								hubListsEmpty
							}
						>
							<GitCompare size={16} />
							{isWorking ? 'Comparaison…' : 'Lancer la réconciliation'}
						</button>
					</div>

					{hubListsEmpty ? (
						<p className="cross-verify-help cross-verify-help--hub">
							<Link to="/import" className="cross-verify-inline-link">
								<FileUp size={14} /> Importer et extraire
							</Link>{' '}
							un document, puis le valider avant de revenir ici.
						</p>
					) : (
						<p className="cross-verify-help cross-verify-help--hub">
							Vous pouvez aussi ouvrir la réconciliation depuis l&apos;historique ou la page
							détail d&apos;un document déjà validé.
						</p>
					)}
				</section>
			</div>
		);
	}

	const partnerImportType = partnerKind === 'invoice' ? 'invoice' : 'declaration';
	const partnerExtractLabel =
		partnerKind === 'invoice'
			? 'Extraire une facture partenaire'
			: 'Extraire une DUM partenaire';
	const partnerListEmpty = !loadingLists && partnerOptions.length === 0;

	const handleExtractPartner = () => {
		navigate(`/import?docType=${partnerImportType}&returnTo=cross-verification`);
	};

	const handleExportReport = () => {
		if (!comparison) {
			return;
		}
		exportComparisonReportPdf({
			comparison,
			dumDetail,
			invoiceDetail,
			comparisonRows,
			amountSummary,
			dossierRef: buildReconciliationPairRef(dumDetail, invoiceDetail, comparison),
			confidence: dumDetail?.score_confiance ?? null,
			issueCount: countComparisonIssues(comparisonRows),
		});
	};

	const handleCancel = () => {
		if (isWorking) {
			return;
		}
		const hasProgress =
			phase === 'compare' || Boolean(partnerId) || Boolean(comparison);
		if (hasProgress) {
			const confirmed = window.confirm(
				'Annuler la réconciliation ? La comparaison en cours ne sera pas conservée pour l\'export ERP.'
			);
			if (!confirmed) {
				return;
			}
		}
		clearCrossVerificationSession();
		navigate(sourceType === 'invoice' ? '/invoice-validation' : '/validation');
	};

	return (
		<div className="cross-verify-page fade-up">
			<WorkflowBreadcrumb
				workflow={sourceType === 'invoice' ? 'invoice' : 'dum'}
				current="cross"
			/>
			<header className="cross-verify-header">
				<div>
					<p className="cross-verify-kicker">Extractions &gt; Comparaison</p>
					<h1>Contrôle de conformité DUM — Facture fournisseur</h1>
					<p className="cross-verify-sub">
						Document source : <strong>{sourceRegisteredLine}</strong>
					</p>
				</div>
				<div className="cross-verify-header-actions">
					<button
						type="button"
						className="cross-verify-btn cancel"
						onClick={handleCancel}
						disabled={isWorking}
					>
						Annuler
					</button>
					<Link
						to={sourceType === 'invoice' ? '/invoice-validation' : '/validation'}
						className="cross-verify-back"
					>
						<ArrowLeft size={16} />
						Retour validation
					</Link>
				</div>
			</header>

			{error ? (
				<div className="cross-verify-alert error">
					<AlertTriangle size={18} />
					<span>{error}</span>
				</div>
			) : null}

			{sourceValidationMessage ? (
				<div className="cross-verify-alert error">
					<AlertTriangle size={18} />
					<span>{sourceValidationMessage}</span>
				</div>
			) : null}

			{phase === 'select' ? (
				<section className="cross-verify-card">
					<h2>Choisir le document de comparaison</h2>
					<p className="cross-verify-help">
						Seuls les documents <strong>validés</strong> apparaissent dans la liste partenaire.
						Sélectionnez la {partnerKind === 'invoice' ? 'facture' : 'DUM'} à rapprocher, puis
						lancez la comparaison.
					</p>

					<div className="cross-verify-source-pill">
						<FileText size={18} />
						<div>
							<span>Source enregistrée</span>
							<strong>{sourceRegisteredLine}</strong>
						</div>
					</div>

					<label className="cross-verify-select-label" htmlFor="partner-doc">
						{partnerKind === 'invoice' ? 'Facture partenaire' : 'DUM partenaire'}
					</label>
					<p className="cross-verify-select-hint">
						{partnerKind === 'invoice'
							? 'Sélection par numéro de facture et date de facture.'
							: 'Sélection par numéro de déclaration et date de déclaration.'}
					</p>
					<select
						id="partner-doc"
						className="cross-verify-select"
						value={partnerId}
						onChange={(e) => setPartnerId(e.target.value)}
						disabled={loadingLists || isWorking}
					>
						<option value="">— Sélectionner —</option>
						{partnerOptions.map((opt) => (
							<option key={opt.id} value={opt.id}>
								{opt.label} · {opt.sub}
								{opt.linkedSuffix ? ` (${opt.linkedSuffix})` : ''}
							</option>
						))}
					</select>

					{partnerListEmpty ? (
						<p className="cross-verify-help cross-verify-help--warn">
							Aucun {partnerKind === 'invoice' ? 'document facture validé' : 'document DUM validé'}{' '}
							disponible. Validez un partenaire via l&apos;étape Validation ou extrayez-en un nouveau.
						</p>
					) : null}

					<p className="cross-verify-actions-help cross-verify-actions-help--inline">
						<strong>Annuler</strong> : quitte la réconciliation (session effacée).{' '}
						<strong>Retour validation</strong> (en-tête) : reprend la correction sans effacer la session.
					</p>
					<div className="cross-verify-actions cross-verify-actions--select">
						<button
							type="button"
							className="cross-verify-btn cancel"
							onClick={handleCancel}
							disabled={isWorking}
						>
							Annuler
						</button>
						<button
							type="button"
							className="cross-verify-btn outline"
							onClick={handleExtractPartner}
							disabled={isWorking}
						>
							<FileUp size={16} />
							{partnerExtractLabel}
						</button>
						<button
							type="button"
							className="cross-verify-btn ghost"
							onClick={loadLists}
							disabled={loadingLists}
						>
							<RefreshCw size={16} />
							Actualiser la liste
						</button>
						<button
							type="button"
							className="cross-verify-btn primary"
							onClick={handleStartCompare}
							disabled={
								!partnerId ||
								isWorking ||
								loadingLists ||
								Boolean(sourceValidationMessage)
							}
						>
							{isWorking ? 'Comparaison...' : 'Comparer les totaux'}
							<ChevronRight size={16} />
						</button>
					</div>
				</section>
			) : null}

			{phase === 'compare' && comparison ? (
				<>
					<section className="cross-verify-sources-grid">
						<article className="cross-verify-source-card">
							<p className="source-tag">Source 1 — DUM</p>
							<h3>
								{dumDetail?.numero_declaration ||
									comparison?.numero_declaration_dum ||
									`DUM #${dumId}`}
							</h3>
							<p className="source-file">
								{dumDetail?.fichier ||
									(sourceType === 'dum'
										? sourceRegisteredLine
										: `Document #${dumId}`)}
							</p>
						</article>
						<article className="cross-verify-source-card">
							<p className="source-tag">Source 2 — Facture</p>
							<h3>
								{invoiceDetail?.numero_facture ||
									comparison?.numero_facture ||
									`Facture #${invoiceId}`}
							</h3>
							<p className="source-file">
								{invoiceDetail?.fichier_nom ||
									(sourceType === 'invoice'
										? sourceRegisteredLine
										: `Facture #${invoiceId}`)}
							</p>
						</article>
					</section>

					<section className="cross-verify-previews-grid">
						<DocumentPreviewPanel
							title="Document DUM"
							subtitle={
								dumDetail?.numero_declaration ||
								comparison?.numero_declaration_dum ||
								`DUM #${dumId}`
							}
							preview={dumPreview}
							loading={previewsLoading && !dumPreview?.dataUrl}
							error={previewErrors.dum}
							editLink={
								isFullyAligned || !dumId
									? undefined
									: `/validation?documentId=${dumId}`
							}
							editLabel="Corriger la DUM"
						/>
						<DocumentPreviewPanel
							title="Document facture"
							subtitle={
								invoiceDetail?.numero_facture ||
								comparison?.numero_facture ||
								`Facture #${invoiceId}`
							}
							preview={invoicePreview}
							loading={previewsLoading && !invoicePreview?.dataUrl}
							error={previewErrors.invoice}
							editLink={
								isFullyAligned || !invoiceId
									? undefined
									: `/invoice-validation?invoiceId=${invoiceId}`
							}
							editLabel="Corriger la facture"
						/>
					</section>

					<div
						className={`cross-verify-conformity-banner ${
							isAmountAligned ? 'is-ok' : 'is-ko'
						}`}
						role="status"
					>
						{isAmountAligned ? <CheckCircle2 size={22} /> : <XCircle size={22} />}
						<div>
							<strong>
								{isAmountAligned
									? 'Montants PFN et NET PAY conformes'
									: 'Écart de montant — non conforme'}
							</strong>
							<p>
								{isAmountAligned
									? 'Les totaux principaux sont alignés (tolérance ±0,01). Vérifiez les lignes secondaires ci-dessous.'
									: `PFN DUM ${formatMoney(totalDum, devise)} ≠ NET PAY ${formatMoney(totalFacture, devise)} — écart ${formatMoney(ecart, devise)}.`}
							</p>
						</div>
					</div>

					<section className="cross-verify-totals-card">
						<div className="totals-block">
							<p>TOTAUX DUM (PFN)</p>
							<strong>{formatMoney(totalDum, devise)}</strong>
						</div>
						<div className={`totals-center ${isAmountAligned ? 'ok' : 'ko'}`}>
							{isAmountAligned ? <CheckCircle2 size={40} /> : <XCircle size={40} />}
							<span className="ecart-badge">
								Écart : {formatMoney(ecart != null ? Math.abs(ecart) : null, devise)}
							</span>
							<button
								type="button"
								className="cross-verify-btn outline"
								onClick={handleRecompare}
								disabled={isWorking}
							>
								<RefreshCw size={16} />
								{isWorking ? '...' : 'Recomparer'}
							</button>
						</div>
						<div className="totals-block">
							<p>TOTAUX FACTURE (NET PAY)</p>
							<strong>{formatMoney(totalFacture, devise || comparison?.devise || '')}</strong>
						</div>
					</section>

					{comparison?.ecart_commentaire ? (
						<p className="cross-verify-comment">{comparison.ecart_commentaire}</p>
					) : null}
					{isAmountAligned && !isFullyAligned ? (
						<p className="cross-verify-comment cross-verify-comment--secondary">
							Les totaux PFN et NET PAY correspondent. Des points d&apos;attention
							(poids, colis, incoterm…) restent listés dans le tableau ci-dessous.
						</p>
					) : null}
					{!isAmountAligned ? (
						<p className="cross-verify-comment cross-verify-comment--error">
							{comparison?.ecart_commentaire ||
								'Corrigez la DUM ou la facture puis cliquez sur Recomparer.'}
						</p>
					) : null}

					<section className="cross-verify-table-card">
						<div className="cross-verify-table-head">
							<h2>Analyse détaillée des écarts</h2>
						</div>
						<div className="cross-verify-table-wrap">
							<table className="cross-verify-table">
								<thead>
									<tr>
										<th>Catégorie</th>
										<th>Valeur DUM</th>
										<th>Valeur facture</th>
										<th>Écart</th>
										<th>Statut</th>
									</tr>
								</thead>
								<tbody>
									{comparisonRows.map((row) => (
										<tr key={row.code}>
											<td>{row.categorie}</td>
											<td>{row.dumValue}</td>
											<td>{row.factureValue}</td>
											<td>{row.ecart}</td>
											<td>
												<span className={`status-pill ${row.tone}`}>{row.statut}</span>
											</td>
										</tr>
									))}
								</tbody>
							</table>
						</div>
					</section>

					<footer className="cross-verify-footer">
						<p>
							Dernière comparaison{' '}
							{comparison?.compared_at
								? new Date(comparison.compared_at).toLocaleString('fr-FR')
								: '—'}
						</p>
						<div className="cross-verify-actions">
							<button
								type="button"
								className="cross-verify-btn cancel"
								onClick={handleCancel}
								disabled={isWorking}
							>
								Annuler
							</button>
							<button
								type="button"
								className="cross-verify-btn ghost"
								onClick={() => {
									updateCrossVerificationSession({
										partnerId: null,
										comparisonResult: null,
										redoReconciliation: true,
									});
									setPartnerId('');
									setPhase('select');
									setComparison(null);
									setDumPreview(null);
									setInvoicePreview(null);
								}}
							>
								Changer de partenaire
							</button>
							<button
								type="button"
								className="cross-verify-btn outline"
								onClick={handleExportReport}
								disabled={isWorking}
							>
								<Download size={16} />
								Exporter PDF
							</button>
							<ErpExportButton
								kind={ERP_EXPORT.DOSSIER}
								invoiceId={invoiceId}
								dumId={dumId}
								reference={buildReconciliationPairRef(
									dumDetail,
									invoiceDetail,
									comparison
								)}
								statutControle={comparison?.statut_controle}
								isAmountAligned={isAmountAligned}
								isAdmin={user?.role === 'admin'}
								disabled={isWorking}
								onError={setError}
								className="cross-verify-btn primary erp-export-btn--dossier"
							/>
						</div>
						<p className="cross-verify-actions-help">
							<strong>Changer de partenaire</strong> : nouvelle comparaison (autre DUM ou facture).{' '}
							<strong>Annuler</strong> : abandonne la réconciliation.{' '}
							<strong>Télécharger le rapport</strong> : CSV du contrôle.{' '}
							<strong>Exporter dossier vers ERP</strong> : DUM + facture + contrôle (PFN = NET PAY requis).
						</p>
					</footer>
				</>
			) : null}
		</div>
	);
}

export default CrossVerificationPage;
