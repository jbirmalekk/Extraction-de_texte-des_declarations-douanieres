import { useEffect, useMemo, useRef, useState } from 'react';
import {
	AlertTriangle,
	CheckCircle2,
	FileText,
	GitCompare,
	RotateCw,
	Save,
	ZoomIn,
	ZoomOut,
} from 'lucide-react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import ErpExportButton from '../components/Erp/ErpExportButton';
import ValidationContextStrip from '../components/ui/ValidationContextStrip';
import WorkflowBreadcrumb from '../components/Workflow/WorkflowBreadcrumb';
import { ERP_EXPORT } from '../utils/erpExport';
import { getWorkflowProgressForValidation } from '../utils/workflowProgress';
import { isInvoiceValidated, RECONCILIATION_BLOCKED_MSG } from '../utils/workflowActions';
import { fieldNeedsCorrection } from '../utils/validationFieldFilters';
import {
	createInvoiceFromUpload,
	fetchInvoiceById,
	fetchInvoicesList,
	patchInvoice,
} from '../services/invoiceApi';
import { useValidationDraft } from '../hooks/useValidationDraft';
import { buildInvoicePatchFromFields } from '../utils/invoiceFields';
import { fileFromStoredInvoiceDocument } from '../utils/invoiceDocumentBlob';
import { resolveInvoiceIdFromStorage } from '../utils/resolveInvoiceId';
import { snapshotPreview } from '../utils/compareDocumentPreview';
import { saveCrossVerificationSession } from '../utils/crossVerificationSession';
import { buildGroupedFilteredFields } from '../utils/validationFieldFilters';
import {
	hydrateInvoiceContextFromApi,
	syncInvoiceLatestFromValidationPayload,
} from '../utils/documentContextStorage';
import { useDocumentFilePreview } from '../hooks/useDocumentFilePreview';
import { useAuth } from '../hooks/useAuth';
import './ValidationPage.css';
import '../components/Workflow/WorkflowBreadcrumb.css';

const NON_EDITABLE_SECTIONS = new Set(['Controle DUM', 'Metadonnees', 'Qualite OCR', 'Listes']);

const safeJsonParse = (value, fallback) => {
	if (!value) {
		return fallback;
	}
	try {
		return JSON.parse(value);
	} catch (_error) {
		return fallback;
	}
};

const formatNow = () => {
	const now = new Date();
	return now.toLocaleString('fr-FR', {
		year: 'numeric',
		month: '2-digit',
		day: '2-digit',
		hour: '2-digit',
		minute: '2-digit',
	});
};

const getConfidenceTone = (confidence) => {
	if (typeof confidence !== 'number') {
		return 'unknown';
	}
	if (confidence >= 90) {
		return 'high';
	}
	if (confidence >= 80) {
		return 'good';
	}
	if (confidence >= 65) {
		return 'medium';
	}
	return 'low';
};

const buildValidationFieldsFromPayload = (payload) => {
	const sourceFields = Array.isArray(payload?.fields) ? payload.fields : [];
	if (sourceFields.length === 0) {
		return [];
	}

	const modifiedMap = payload?.modifiedFields || {};

	return sourceFields
		.filter((field) => !NON_EDITABLE_SECTIONS.has(field?.section || ''))
		.map((field, index) => {
			const fieldId = field?.id || field?.key || `field_${index}`;
			const fieldKey = field?.key || fieldId;
			const persisted = modifiedMap[fieldId] || modifiedMap[fieldKey] || null;
			const value = String(field?.value ?? '').trim();
			const confidence = typeof field?.confidence === 'number' ? field.confidence : 75;

			return {
				id: fieldId,
				key: fieldKey,
				label: field?.label || field?.key || `Field ${index + 1}`,
				section: field?.section || 'Autres',
				value,
				confidence,
				hasError: Boolean(field?.hasError),
				ocrOriginal: String(persisted?.ocrOriginal ?? value).trim(),
				modifiedBy: persisted?.modifiedBy || null,
				modifiedAt: persisted?.modifiedAt || null,
				isManual: Boolean(field?.isManual),
			};
		});
};

const buildModifiedMap = (fields) =>
	fields.reduce((acc, field) => {
		if (String(field.value ?? '') !== String(field.ocrOriginal ?? '')) {
			acc[field.id] = {
				value: field.value,
				ocrOriginal: field.ocrOriginal,
				modifiedBy: field.modifiedBy,
				modifiedAt: field.modifiedAt,
			};
		}
		return acc;
	}, {});

const resolveRouteInvoiceId = (location, searchParams) => {
	const fromState = Number(location.state?.invoiceId);
	if (Number.isFinite(fromState) && fromState > 0) {
		return fromState;
	}
	const fromQuery = Number(searchParams.get('invoiceId'));
	if (Number.isFinite(fromQuery) && fromQuery > 0) {
		return fromQuery;
	}
	return null;
};

function InvoiceValidationPage() {
	const navigate = useNavigate();
	const location = useLocation();
	const [searchParams] = useSearchParams();
	const queryInvoiceId = searchParams.get('invoiceId');
	const { user } = useAuth();
	const routeInvoiceId = resolveRouteInvoiceId(location, searchParams);
	const [payload, setPayload] = useState(null);
	const [initLoading, setInitLoading] = useState(false);
	const [initError, setInitError] = useState('');
	const [fields, setFields] = useState([]);
	const [toast, setToast] = useState(null);
	const [isFinalValidating, setIsFinalValidating] = useState(false);
	const [readyForErp, setReadyForErp] = useState(false);
	const [isCrossVerifying, setIsCrossVerifying] = useState(false);
	const [resolvedInvoiceId, setResolvedInvoiceId] = useState(routeInvoiceId);
	const [invoiceMeta, setInvoiceMeta] = useState(null);
	const [invoiceBackendMissing, setInvoiceBackendMissing] = useState(false);
	const [isCheckingBackend, setIsCheckingBackend] = useState(false);
	const [isRegisteringInBackend, setIsRegisteringInBackend] = useState(false);
	const [zoom, setZoom] = useState(100);
	const [rotation, setRotation] = useState(0);
	const [showOnlyNeedsCorrection, setShowOnlyNeedsCorrection] = useState(false);
	const [fieldSortBy, setFieldSortBy] = useState('section');
	const timeoutRef = useRef(null);

	useEffect(() => {
		let isActive = true;

		const init = async () => {
			setInitError('');
			const targetId = routeInvoiceId;
			if (targetId != null) {
				setInitLoading(true);
			}

			try {
				let savedPayload = safeJsonParse(localStorage.getItem('invoice_validation_payload'), null);
				const payloadId = Number(
					savedPayload?.invoiceId ?? savedPayload?.backendId
				);
				const fromHistory = Boolean(location.state?.fromHistory);
				const shouldHydrate =
					targetId != null &&
					(fromHistory ||
						!savedPayload ||
						!Number.isFinite(payloadId) ||
						payloadId <= 0 ||
						Number(payloadId) !== Number(targetId) ||
						!savedPayload?.source?.dataUrl);

				if (shouldHydrate) {
					const idToLoad = targetId ?? payloadId;
					try {
						await hydrateInvoiceContextFromApi(idToLoad);
						if (!isActive) {
							return;
						}
						savedPayload = safeJsonParse(
							localStorage.getItem('invoice_validation_payload'),
							null
						);
					} catch (error) {
						const detail = error?.response?.data?.detail;
						if (isActive) {
							setInitError(
								typeof detail === 'string'
									? detail
									: 'Impossible de charger cette facture pour la validation.'
							);
						}
					}
				}

				if (!isActive) {
					return;
				}

				const resolvedId = Number(
					targetId ?? savedPayload?.invoiceId ?? savedPayload?.backendId
				);
				if (Number.isFinite(resolvedId) && resolvedId > 0) {
					setResolvedInvoiceId(resolvedId);
				}

				if (savedPayload?.rawResult) {
					setInvoiceMeta({
						fichier_nom: savedPayload.rawResult.fichier_nom,
						content_type: savedPayload.rawResult.content_type,
						dossier: savedPayload.rawResult.dossier,
					});
				}

				if (
					savedPayload?.source?.dataUrl &&
					targetId != null &&
					Number(savedPayload?.invoiceId ?? savedPayload?.backendId) !== Number(targetId)
				) {
					const { dataUrl: _drop, ...sourceMeta } = savedPayload.source;
					savedPayload = { ...savedPayload, source: sourceMeta };
				}

				setPayload(savedPayload);
				setFields(buildValidationFieldsFromPayload(savedPayload));
			} finally {
				if (isActive) {
					setInitLoading(false);
				}
			}
		};

		init();

		return () => {
			isActive = false;
			if (timeoutRef.current) {
				window.clearTimeout(timeoutRef.current);
			}
		};
	}, [location.key, location.state?.invoiceId, queryInvoiceId, routeInvoiceId]);

	useEffect(() => {
		let cancelled = false;

		const lookupInvoiceByNumero = async (numero) => {
			if (!numero) {
				return null;
			}
			const listPage = await fetchInvoicesList({ limit: 200 }, user);
			const hit = listPage.items.find(
				(row) => String(row.numero_facture || '').trim() === numero
			);
			if (!hit?.id) {
				return null;
			}
			return fetchInvoiceById(hit.id);
		};

		const syncResolvedInvoice = (inv) => {
			setResolvedInvoiceId(inv.id);
			setInvoiceMeta({
				fichier_nom: inv.fichier_nom,
				content_type: inv.content_type,
				dossier: inv.dossier,
			});
			if (payload) {
				const synced = {
					...payload,
					backendId: inv.id,
					invoiceId: inv.id,
					rawResult: inv,
					source: payload.source,
				};
				setPayload(synced);
				localStorage.setItem('invoice_validation_payload', JSON.stringify(synced));
			}
		};

		const verifyInvoiceInBackend = async () => {
			const candidateId = resolveInvoiceIdFromStorage(payload);
			const numField = (payload?.fields || fields).find((f) => f.key === 'numero_facture');
			const numero = String(numField?.value ?? '').trim();

			if (!candidateId && !numero) {
				setResolvedInvoiceId(null);
				setInvoiceBackendMissing(false);
				return;
			}

			setIsCheckingBackend(true);
			setInvoiceBackendMissing(false);

			try {
				let inv = null;
				if (candidateId) {
					try {
						inv = await fetchInvoiceById(candidateId);
					} catch (error) {
						if (error?.response?.status !== 404) {
							throw error;
						}
					}
				}
				if (!inv && numero) {
					inv = await lookupInvoiceByNumero(numero);
				}
				if (!inv) {
					setResolvedInvoiceId(null);
					setInvoiceBackendMissing(true);
					return;
				}
				if (cancelled) {
					return;
				}
				syncResolvedInvoice(inv);
				return;
			} catch (error) {
				if (cancelled) {
					return;
				}
				const status = error?.response?.status;
				if (status !== 404) {
					if (candidateId) {
						setResolvedInvoiceId(candidateId);
					}
					return;
				}

				try {
					const inv = numero ? await lookupInvoiceByNumero(numero) : null;
					if (inv && !cancelled) {
						syncResolvedInvoice(inv);
						return;
					}
				} catch {
					// ignore
				}

				setResolvedInvoiceId(null);
				setInvoiceBackendMissing(true);
			} finally {
				if (!cancelled) {
					setIsCheckingBackend(false);
				}
			}
		};

		if (payload) {
			verifyInvoiceInBackend();
		}

		return () => {
			cancelled = true;
		};
	}, [payload?.backendId, payload?.savedAt, user?.id]);

	const showToast = (type, message) => {
		setToast({ type, message });
		if (timeoutRef.current) {
			window.clearTimeout(timeoutRef.current);
		}
		timeoutRef.current = window.setTimeout(() => setToast(null), 2800);
	};

	const previewEntityId =
		resolvedInvoiceId ?? payload?.invoiceId ?? payload?.backendId ?? null;

	const { preview, loading: previewLoading, error: previewError, reload: reloadPreview } = useDocumentFilePreview({
		kind: 'invoice',
		entityId: previewEntityId,
		payloadSource: payload?.source,
		fileName: invoiceMeta?.fichier_nom || payload?.source?.name || payload?.rawResult?.fichier_nom,
		contentType: invoiceMeta?.content_type || payload?.source?.type || payload?.rawResult?.content_type,
		sourceFileAvailable: payload?.rawResult?.has_source_file ?? invoiceMeta?.has_source_file,
	});

	const handlePreviewMediaError = () => {
		reloadPreview();
	};

	const displayPreview = preview?.dataUrl ? preview : null;

	const isPdf = Boolean(displayPreview?.type?.toLowerCase().includes('pdf'));

	const modifiedCount = Object.keys(buildModifiedMap(fields)).length;
	const emptyFieldsCount = fields.filter((field) => !String(field?.value ?? '').trim()).length;
	const lowConfidenceCount = fields.filter(
		(field) => typeof field.confidence === 'number' && field.confidence < 80
	).length;
	const hasValidationPayload = Boolean(payload) && fields.length > 0;
	const hasStoredFile = Boolean(displayPreview?.dataUrl);
	const hasBackendLink = Boolean(previewEntityId);

	const groupedFields = useMemo(
		() =>
			buildGroupedFilteredFields(fields, {
				showOnlyNeedsCorrection,
				sortBy: fieldSortBy,
				excludeSections: NON_EDITABLE_SECTIONS,
			}),
		[fields, showOnlyNeedsCorrection, fieldSortBy]
	);

	const { isDirty, lastSavedLabel, autoSaving, persistDraft, markDraftSaved } = useValidationDraft({
		storageKey: 'invoice_validation_payload',
		fields,
		payload,
		setPayload,
		buildModifiedMap,
		enabled: hasValidationPayload,
	});

	const invoiceWorkflowSteps = [
		{ n: 1, label: 'Enregistrer en base', done: hasBackendLink, active: invoiceBackendMissing },
		{ n: 2, label: 'Corriger les champs', done: hasBackendLink && !isDirty, active: hasBackendLink },
		{ n: 3, label: 'Réconciliation DUM', done: false, active: false },
		{ n: 4, label: 'Export ERP', done: readyForErp, active: readyForErp },
	];
	const documentLabel = payload?.documentId ?? resolvedInvoiceId ?? 'Facture';
	const connectionLabel = hasBackendLink
		? `Facture #${resolvedInvoiceId}`
		: invoiceBackendMissing
			? 'Non trouvee en base'
			: 'Mode local';

	const updateFieldValue = (fieldId, value) => {
		const actor = user?.username || 'Utilisateur courant';
		const timestamp = formatNow();

		setFields((prev) =>
			prev.map((field) =>
				field.id === fieldId
					? {
							...field,
							value,
							hasError: false,
							modifiedBy: actor,
							modifiedAt: timestamp,
						}
					: field
			)
		);
	};

	const handleResetForm = () => {
		const confirmed = window.confirm(
			'Réinitialiser tous les champs aux valeurs OCR d\'origine ?'
		);
		if (!confirmed) {
			return;
		}
		setFields((prev) =>
			prev.map((field) => ({
				...field,
				value: field.ocrOriginal,
				hasError: false,
				modifiedBy: null,
				modifiedAt: null,
			}))
		);
		markDraftSaved();
		showToast('info', 'Formulaire réinitialisé aux données OCR d\'origine.');
	};

	const handleSaveChanges = () => {
		if (persistDraft()) {
			markDraftSaved();
			showToast('success', 'Brouillon enregistré localement.');
		}
	};

	const persistInvoiceToBackend = async ({ markValidated = false } = {}) => {
		const invoiceId = resolvedInvoiceId ?? resolveInvoiceIdFromStorage(payload);
		if (!invoiceId) {
			throw new Error(
				'Facture introuvable en base. Reimportez le fichier depuis Import (type Facture), puis rouvrez la validation.'
			);
		}
		const patch = buildInvoicePatchFromFields(fields);
		if (markValidated) {
			patch.statut = 'valide';
		} else {
			patch.statut = 'controle_croise';
		}
		let updated;
		try {
			updated = await patchInvoice(invoiceId, patch);
		} catch (error) {
			if (error?.response?.status === 404) {
				throw new Error(
					`Facture #${invoiceId} introuvable sur le serveur factures (port 8001). ` +
						'Reimportez le document : la base actuelle ne contient peut-etre plus cette facture.'
				);
			}
			throw error;
		}

		const modifiedFields = buildModifiedMap(fields);
		const finalAudit = {
			...(payload || {}),
			fields,
			modifiedFields,
			validatedAt: new Date().toISOString(),
			rawResult: updated,
		};
		localStorage.setItem('invoice_last_validated', JSON.stringify(finalAudit));
		localStorage.setItem(
			'invoice_latest_result',
			JSON.stringify({
				invoiceId: updated.id,
				backendId: updated.id,
				documentId: updated.numero_facture || `FACT-${updated.id}`,
				fields,
				rawResult: updated,
				savedAt: finalAudit.validatedAt,
			})
		);
		return updated;
	};

	const handleFinalValidate = async () => {
		if (!hasBackendLink) {
			showToast(
				'error',
				'Validation impossible : identifiant facture manquant. Recommencez depuis Import.'
			);
			return;
		}

		if (isFinalValidating || isCrossVerifying) {
			return;
		}

		setIsFinalValidating(true);
		try {
			await persistInvoiceToBackend({ markValidated: true });
			setReadyForErp(true);
			showToast(
				'success',
				'Facture validée. Envoyez-la vers l’ERP ou lancez la vérification croisée.'
			);
			setIsFinalValidating(false);
		} catch (error) {
			const detail = error?.response?.data?.detail;
			showToast(
				'error',
				typeof detail === 'string'
					? detail
					: error?.message || 'Validation finale echouee, veuillez reessayer.'
			);
			setIsFinalValidating(false);
		}
	};

	const handleRegisterInBackend = async () => {
		if (isRegisteringInBackend || isCheckingBackend) {
			return;
		}
		setIsRegisteringInBackend(true);
		try {
			const file = await fileFromStoredInvoiceDocument();
			if (!file) {
				throw new Error(
					'Fichier facture introuvable dans le navigateur. Reimportez le PDF depuis la page Import.'
				);
			}
			const created = await createInvoiceFromUpload(file);
			if (!created?.id) {
				throw new Error('Creation facture echouee (id manquant). Verifiez back_EMP_Fact.');
			}
			const patch = buildInvoicePatchFromFields(fields);
			patch.statut = 'extracted';
			const updated = await patchInvoice(created.id, patch);

			setResolvedInvoiceId(updated.id);
			setInvoiceBackendMissing(false);

			const modifiedFields = buildModifiedMap(fields);
			const synced = {
				...(payload || {}),
				backendId: updated.id,
				invoiceId: updated.id,
				rawResult: updated,
				fields,
				modifiedFields,
				savedAt: new Date().toISOString(),
			};
			setPayload(synced);
			localStorage.setItem('invoice_validation_payload', JSON.stringify(synced));
			localStorage.setItem(
				'invoice_latest_result',
				JSON.stringify({
					invoiceId: updated.id,
					backendId: updated.id,
					documentId: updated.numero_facture || `FACT-${updated.id}`,
					fields,
					rawResult: updated,
					savedAt: synced.savedAt,
				})
			);

			showToast('success', `Facture enregistree en base (id #${updated.id}).`);
		} catch (error) {
			const detail = error?.response?.data?.detail;
			showToast(
				'error',
				typeof detail === 'string'
					? detail
					: error?.message || 'Enregistrement en base echoue.'
			);
		} finally {
			setIsRegisteringInBackend(false);
		}
	};

	const goToInvoiceResults = async () => {
		await syncInvoiceLatestFromValidationPayload();
		const invId = payload?.invoiceId ?? payload?.backendId;
		navigate(invId ? `/invoice-ocr-result?invoiceId=${invId}` : '/invoice-ocr-result');
	};

	const handleCancel = () => {
		if (isFinalValidating || isCrossVerifying || isRegisteringInBackend) {
			return;
		}
		if (modifiedCount > 0) {
			const confirmed = window.confirm(
				'Annuler la validation ? Les modifications non enregistrées seront perdues.'
			);
			if (!confirmed) {
				return;
			}
		}
		goToInvoiceResults();
	};

	const handleCrossVerification = async () => {
		if (!hasBackendLink) {
			showToast('error', 'Enregistrement impossible : identifiant facture manquant.');
			return;
		}
		if (isFinalValidating || isCrossVerifying) {
			return;
		}
		const alreadyValidated =
			readyForErp || isInvoiceValidated(payload?.rawResult?.statut);
		if (!alreadyValidated) {
			showToast('error', RECONCILIATION_BLOCKED_MSG);
			return;
		}

		setIsCrossVerifying(true);
		try {
			const updated = await persistInvoiceToBackend({ markValidated: false });
			const numField = fields.find((f) => f.key === 'numero_facture');
			const dateField = fields.find((f) => f.key === 'date_facture');
			saveCrossVerificationSession({
				sourceType: 'invoice',
				sourceId: updated.id,
				sourceNumero: numField?.value || null,
				sourceDate: dateField?.value || null,
				sourceLabel: numField?.value || null,
				sourceFileName:
					payload?.documentId || preview?.name || updated.fichier_nom || `Facture_${updated.id}.pdf`,
				sourcePreview: snapshotPreview(preview),
				invoiceId: updated.id,
				invoicePreview: snapshotPreview(preview),
			});
			showToast('success', 'Facture enregistree. Choisissez la DUM a comparer.');
			navigate('/cross-verification');
		} catch (error) {
			const detail = error?.response?.data?.detail;
			showToast(
				'error',
				typeof detail === 'string' ? detail : error?.message || 'Enregistrement echoue.'
			);
			setIsCrossVerifying(false);
		}
	};

	const increaseZoom = () => setZoom((prev) => Math.min(prev + 25, 200));
	const decreaseZoom = () => setZoom((prev) => Math.max(prev - 25, 50));
	const rotateDocument = () => setRotation((prev) => (prev + 90) % 360);

	const handlePreviewWheel = (event) => {
		if (event.ctrlKey || event.metaKey) {
			event.preventDefault();
			if (event.deltaY < 0) {
				increaseZoom();
			} else {
				decreaseZoom();
			}
		}
	};

	const renderFieldCard = (field) => {
		const tone = getConfidenceTone(field.confidence);
		const confidenceLabel = typeof field.confidence === 'number' ? `${field.confidence}%` : 'N/A';
		const value = String(field.value ?? '').trim();
		const originalValue = String(field.ocrOriginal ?? '').trim();
		const hasChanged = value !== originalValue;

		return (
			<div
				key={field.id}
				className={`validated-input-card ${field.hasError ? 'has-error' : ''} ${hasChanged ? 'is-modified' : ''} ${value ? 'is-filled' : 'is-empty'}`}
			>
				<div className="validated-input-head">
					<label htmlFor={field.id}>{field.label}</label>
					<div className="validated-badges">
						<span className={`confidence-badge ${tone}`}>{confidenceLabel}</span>
						{field.isManual && <span className="validation-manual-badge">Manuel</span>}
						{typeof field.confidence === 'number' && field.confidence < 80 && (
							<AlertTriangle size={16} className="low-confidence" />
						)}
					</div>
				</div>

				<div className="validated-input-wrap">
					<input
						id={field.id}
						type="text"
						value={field.value}
						placeholder={originalValue || 'Entrez la valeur...'}
						onChange={(event) => updateFieldValue(field.id, event.target.value)}
					/>
				</div>

				<div className="validation-field-meta">
					<p>
						<span>OCR originale</span>
						{originalValue || '—'}
					</p>
					<p>
						<span>Modifie par</span>
						{field.modifiedBy || 'Non modifie'}
					</p>
					<p>
						<span>Date</span>
						{field.modifiedAt || '—'}
					</p>
				</div>
			</div>
		);
	};

	if (initLoading) {
		return (
			<div className="validation-page fade-up">
				<section className="validation-card validation-empty-card">
					<p>Chargement de la facture…</p>
				</section>
			</div>
		);
	}

	if (!hasValidationPayload) {
		return (
			<div className="validation-page fade-up">
				<section className="validation-header-shell">
					<div className="validation-brand-wrap">
						<div className="validation-brand-mark">EMP</div>
						<div>
							<p className="validation-kicker">Validation facture</p>
							<h1>Formulaire de validation facture</h1>
							<p>Ouvrez cette page depuis les resultats facture pour conserver le formulaire.</p>
						</div>
					</div>
					<span className="validation-doc-badge">Aucune donnee chargee</span>
				</section>

				<section className="validation-card validation-empty-card">
					<AlertTriangle size={32} />
					<h2>Aucun formulaire a valider</h2>
					<p>
						{initError ||
							'Le payload de validation est vide ou a ete perdu. Retournez a la page resultats facture puis relancez la validation depuis ce document.'}
					</p>
					<button type="button" className="history-link-btn" onClick={goToInvoiceResults}>
						Retour aux resultats facture
					</button>
				</section>
			</div>
		);
	}

	return (
		<div className="validation-page fade-up">
			{toast ? <div className={`validation-toast ${toast.type}`}>{toast.message}</div> : null}

			<WorkflowBreadcrumb
				workflow="invoice"
				current="validation"
				stepToOverrides={{
					ocr: (resolvedInvoiceId || payload?.backendId || payload?.invoiceId)
						? `/invoice-ocr-result?invoiceId=${resolvedInvoiceId || payload?.backendId || payload?.invoiceId}`
						: '/invoice-ocr-result',
				}}
			/>

			<ValidationContextStrip
				type="invoice"
				reference={
					fields.find((f) => f.key === 'numero_facture')?.value || documentLabel
				}
				fileName={displayPreview?.name || payload?.documentId}
				fieldsToCorrect={fields.filter((f) => fieldNeedsCorrection(f)).length}
				totalFields={fields.length}
				workflowSteps={getWorkflowProgressForValidation({
					validated: readyForErp,
					reconciled: false,
				})}
			/>

			<section className="validation-header-shell">
				<div className="validation-brand-wrap">
					<div className="validation-brand-mark">EMP</div>
					<div>
						<p className="validation-kicker">Validation facture</p>
						<h1>Contrôle et correction avant validation</h1>
						<p>
							Vérifiez les montants (Gross, NET PAY), le client et les lignes article avant
							enregistrement définitif.
						</p>
					</div>
				</div>
				<div className="validation-header-meta">
					<span className="validation-doc-badge">
						{documentLabel} — {connectionLabel}
					</span>
					{isDirty ? (
						<span className="validation-draft-badge is-unsaved">Non enregistré</span>
					) : (
						<span className="validation-draft-badge is-saved">
							Brouillon enregistré{lastSavedLabel ? ` · ${lastSavedLabel}` : ''}
							{autoSaving ? ' (auto…)' : ''}
						</span>
					)}
				</div>
			</section>

			<div className="validation-workflow-steps" aria-label="Étapes du parcours facture">
				{invoiceWorkflowSteps.map((step) => (
					<div
						key={step.n}
						className={`validation-workflow-step${step.done ? ' done' : ''}${step.active && !step.done ? ' active' : ''}`}
					>
						<span className="validation-workflow-step-num">{step.n}</span>
						{step.label}
					</div>
				))}
			</div>

			<div className="validation-layout-grid">
				<aside className="validation-preview-column">
					<div className="validation-card preview-card-sticky">
						<div className="preview-card-head">
							<h2>Apercu du document</h2>
							<div className="preview-controls">
								<button type="button" onClick={decreaseZoom} disabled={zoom <= 50} aria-label="Dezoomer">
									<ZoomOut size={16} />
								</button>
								<span>{zoom}%</span>
								<button type="button" onClick={increaseZoom} disabled={zoom >= 200} aria-label="Zoomer">
									<ZoomIn size={16} />
								</button>
								<button type="button" onClick={rotateDocument} aria-label="Pivoter">
									<RotateCw size={16} />
								</button>
							</div>
						</div>

						<div className="preview-viewport" onWheel={handlePreviewWheel}>
							<div className="preview-transform-layer">
								{displayPreview?.dataUrl ? (
									isPdf ? (
										<iframe
											title="Document PDF"
											src={displayPreview.dataUrl}
											className="preview-pdf"
											style={{ width: `${zoom}%` }}
											onError={handlePreviewMediaError}
										/>
									) : (
										<img
											src={displayPreview.dataUrl}
											alt="Facture"
											className="preview-image"
											style={{
												width: `${zoom}%`,
												transform: rotation ? `rotate(${rotation}deg)` : undefined,
												transformOrigin: 'center center',
											}}
											onError={handlePreviewMediaError}
										/>
									)
								) : (
									<div className="preview-placeholder">
										<FileText size={52} />
										<p>
											{previewLoading
												? 'Chargement de l\u2019aperçu depuis la GED…'
												: 'Apercu du document'}
										</p>
										{previewError ? (
											<p className="preview-placeholder-error">{previewError}</p>
										) : null}
									</div>
								)}
							</div>
						</div>

						<p className="preview-note">Utilisez Ctrl + molette pour zoomer</p>
					</div>
				</aside>

				<section className="validation-form-column">
					<div className="validation-card smart-form-card">
						<div className="smart-form-head">
							<div>
								<h2>Formulaire de validation facture</h2>
								<p>Corrigez les champs extraits puis validez definitivement.</p>
							</div>
							<span>{modifiedCount} modification(s)</span>
						</div>

						<div
							className={`validation-info-banner ${invoiceBackendMissing ? 'is-error' : ''}`}
						>
							<AlertTriangle size={16} />
							<div>
								<p>
									{invoiceBackendMissing
										? `La facture #${payload?.backendId ?? '?'} n'existe pas en base SQL (table vide ou session obsolete).`
										: isCheckingBackend
											? 'Verification de la facture en base...'
											: emptyFieldsCount > 0
												? `${emptyFieldsCount} champ(s) sont vides.`
												: 'Tous les champs editables contiennent deja une valeur.'}
									{!invoiceBackendMissing && lowConfidenceCount > 0
										? ` ${lowConfidenceCount} champ(s) ont une confiance faible.`
										: ''}
								</p>
								{invoiceBackendMissing ? (
									<div className="validation-recover-row">
										{hasStoredFile ? (
											<button
												type="button"
												className="action-btn save"
												onClick={handleRegisterInBackend}
												disabled={isRegisteringInBackend}
											>
												<Save size={16} />
												{isRegisteringInBackend
													? 'Enregistrement...'
													: 'Enregistrer la facture en base'}
											</button>
										) : null}
										<Link to="/import" className="validation-inline-link">
											Reimporter depuis Import
										</Link>
									</div>
								) : null}
							</div>
						</div>

						<div className="validation-filters-row">
							<label className="validation-filter-check">
								<input
									type="checkbox"
									checked={showOnlyNeedsCorrection}
									onChange={(e) => setShowOnlyNeedsCorrection(e.target.checked)}
								/>
								Afficher seulement les champs à corriger
							</label>
							<label className="validation-filter-sort">
								<span>Trier par</span>
								<select
									value={fieldSortBy}
									onChange={(e) => setFieldSortBy(e.target.value)}
								>
									<option value="section">Section</option>
									<option value="confidence-asc">Confiance (croissant)</option>
									<option value="confidence-desc">Confiance (décroissant)</option>
								</select>
							</label>
						</div>

						<div className="validation-field-list">
							{groupedFields.length === 0 ? (
								<p className="validation-empty-state">Aucun champ éditable à afficher.</p>
							) : (
								groupedFields.map(([sectionName, sectionFields]) => (
									<div key={sectionName} className="validation-section-block">
										<div className="validation-section-head">
											<p className="validation-section-title">{sectionName}</p>
											<span className="validation-section-count">
												{sectionFields.length} champ(s)
											</span>
										</div>
										<div className="validation-section-fields">
											{sectionFields.map(renderFieldCard)}
										</div>
									</div>
								))
							)}
						</div>

						<div className="validation-actions-row">
							<div className="validation-actions-secondary">
								<button
									type="button"
									className="action-btn cancel"
									onClick={handleCancel}
									disabled={
										isFinalValidating ||
										isCrossVerifying ||
										isRegisteringInBackend
									}
									title="Quitter vers les résultats OCR facture"
								>
									Annuler
								</button>
								<button
									type="button"
									className="action-btn reset"
									onClick={handleResetForm}
									disabled={isFinalValidating || isCrossVerifying || isRegisteringInBackend}
								>
									<RotateCw size={16} />
									Réinitialiser
								</button>
								<button
									type="button"
									className="action-btn save"
									onClick={handleSaveChanges}
									disabled={isFinalValidating || isCrossVerifying || isRegisteringInBackend}
								>
									<Save size={16} />
									Enregistrer brouillon
								</button>
							</div>
							<div className="validation-actions-primary">
								<button
									type="button"
									className="action-btn cross-verify"
									onClick={handleCrossVerification}
									disabled={
										isCrossVerifying ||
										isFinalValidating ||
										!hasBackendLink ||
										isCheckingBackend ||
										invoiceBackendMissing ||
										isRegisteringInBackend ||
										(!readyForErp &&
											!isInvoiceValidated(payload?.rawResult?.statut))
									}
									title={
										!readyForErp && !isInvoiceValidated(payload?.rawResult?.statut)
											? RECONCILIATION_BLOCKED_MSG
											: undefined
									}
								>
									<GitCompare size={16} />
									{isCrossVerifying ? 'Enregistrement…' : 'Vérification croisée'}
								</button>
								<button
									type="button"
									className="action-btn final"
									onClick={handleFinalValidate}
									disabled={
										isFinalValidating ||
										isCrossVerifying ||
										!hasBackendLink ||
										isCheckingBackend ||
										invoiceBackendMissing ||
										isRegisteringInBackend
									}
								>
									<CheckCircle2 size={16} className={isFinalValidating ? 'pulse-check' : ''} />
									{isFinalValidating ? 'Validation…' : 'Valider la facture'}
								</button>
								<ErpExportButton
									kind={ERP_EXPORT.INVOICE}
									invoiceId={resolvedInvoiceId || payload?.backendId}
									reference={
										fields.find((f) => f.key === 'numero_facture')?.value ||
										payload?.documentId
									}
									disabled={
										!readyForErp ||
										isFinalValidating ||
										isCrossVerifying ||
										!hasBackendLink
									}
								/>
							</div>
						</div>
						<p className="validation-actions-help">
							<strong>Étape 1</strong> : enregistrez la facture en base si nécessaire.{' '}
							<strong>Valider la facture</strong> avant la vérification croisée.{' '}
							<strong>Enregistrer brouillon</strong> : sauvegarde locale (auto toutes les 30 s).
						</p>
					</div>
				</section>
			</div>

			<div className="validation-footer-links">
				<button type="button" className="text-link" onClick={goToInvoiceResults}>
					Retour aux resultats facture
				</button>
			</div>
		</div>
	);
}

export default InvoiceValidationPage;
