import { useEffect, useMemo, useRef, useState } from 'react';
import {
	AlertTriangle,
	CheckCircle2,
	FileText,
	GitCompare,
	Pencil,
	Plus,
	RotateCw,
	Save,
	Trash2,
	ZoomIn,
	ZoomOut,
} from 'lucide-react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import ErpExportButton from '../components/Erp/ErpExportButton';
import WorkflowBreadcrumb from '../components/Workflow/WorkflowBreadcrumb';
import { ERP_EXPORT } from '../utils/erpExport';
import { fetchLatestOcrCorrections, validateOcrDocument } from '../services/ocrService';
import { useValidationDraft } from '../hooks/useValidationDraft';
import { buildBackendValidationPayload } from '../utils/ocrFields';
import { snapshotPreview } from '../utils/compareDocumentPreview';
import { saveCrossVerificationSession } from '../utils/crossVerificationSession';
import { buildGroupedFilteredFields } from '../utils/validationFieldFilters';
import {
	hydrateDumContextFromApi,
	syncDumLatestFromValidationPayload,
} from '../utils/documentContextStorage';
import { useDocumentFilePreview } from '../hooks/useDocumentFilePreview';
import { useAuth } from '../hooks/useAuth';
import './ValidationPage.css';
import '../components/Workflow/WorkflowBreadcrumb.css';

const NON_EDITABLE_SECTIONS = new Set(['Listes', 'Qualite OCR', 'Metadonnees']);

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

const getAuditActionMeta = (actionType) => {
	const normalized = String(actionType || '').trim().toLowerCase();
	if (normalized === 'add') {
		return { label: 'Ajout', tone: 'add', Icon: Plus };
	}
	if (normalized === 'delete') {
		return { label: 'Suppression', tone: 'delete', Icon: Trash2 };
	}
	if (normalized === 'update') {
		return { label: 'Modification', tone: 'update', Icon: Pencil };
	}
	return { label: '—', tone: 'unknown', Icon: null };
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
				backendOldValue: null,
				backendNewValue: null,
				backendActionType: null,
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

const mergeBackendCorrectionsIntoFields = (fields, latestCorrections) =>
	fields.map((field) => {
		const history = latestCorrections?.[field.key] || latestCorrections?.[field.id];
		if (!history) {
			return field;
		}

		return {
			...field,
			modifiedBy: history.modified_by_username || field.modifiedBy || null,
			modifiedAt: history.modified_at || field.modifiedAt || null,
			backendOldValue: history.old_value ?? null,
			backendNewValue: history.new_value ?? null,
			backendActionType: history.action_type ?? null,
		};
	});

const resolveRouteDocumentId = (location, searchParams) => {
	const fromState = Number(location.state?.documentId);
	if (Number.isFinite(fromState) && fromState > 0) {
		return fromState;
	}
	const fromQuery = Number(searchParams.get('documentId'));
	if (Number.isFinite(fromQuery) && fromQuery > 0) {
		return fromQuery;
	}
	return null;
};

function ValidationPage() {
	const navigate = useNavigate();
	const location = useLocation();
	const [searchParams] = useSearchParams();
	const { user } = useAuth();
	const routeDocumentId = resolveRouteDocumentId(location, searchParams);
	const queryDocumentId = searchParams.get('documentId');
	const [payload, setPayload] = useState(null);
	const [initLoading, setInitLoading] = useState(false);
	const [initError, setInitError] = useState('');
	const [resolvedDocumentId, setResolvedDocumentId] = useState(routeDocumentId);

	useEffect(() => {
		if (routeDocumentId != null) {
			setResolvedDocumentId(routeDocumentId);
		}
	}, [routeDocumentId]);
	const [fields, setFields] = useState([]);
	const [toast, setToast] = useState(null);
	const [isFinalValidating, setIsFinalValidating] = useState(false);
	const [isCrossVerifying, setIsCrossVerifying] = useState(false);
	const [readyForErp, setReadyForErp] = useState(false);
	const [zoom, setZoom] = useState(100);
	const [rotation, setRotation] = useState(0);
	const [showOnlyNeedsCorrection, setShowOnlyNeedsCorrection] = useState(false);
	const [fieldSortBy, setFieldSortBy] = useState('section');
	const timeoutRef = useRef(null);

	useEffect(() => {
		let isActive = true;

		const init = async () => {
			setInitError('');
			const targetId = resolveRouteDocumentId(location, searchParams);
			if (targetId != null) {
				setInitLoading(true);
			}

			try {
				if (targetId != null) {
					setResolvedDocumentId(targetId);
				}

				let savedPayload = safeJsonParse(localStorage.getItem('ocr_validation_payload'), null);
				const payloadId = Number(savedPayload?.backendId);
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
					try {
						await hydrateDumContextFromApi(targetId);
						if (!isActive) {
							return;
						}
						savedPayload = safeJsonParse(localStorage.getItem('ocr_validation_payload'), null);
					} catch (error) {
						const detail = error?.response?.data?.detail;
						const message =
							typeof detail === 'string'
								? detail
								: 'Impossible de charger ce document pour la validation.';
						if (isActive) {
							setInitError(message);
						}
					}
				}

				if (!isActive) {
					return;
				}

				if (
					savedPayload?.source?.dataUrl &&
					targetId != null &&
					Number(savedPayload?.backendId) !== Number(targetId)
				) {
					const { dataUrl: _drop, ...sourceMeta } = savedPayload.source;
					savedPayload = { ...savedPayload, source: sourceMeta };
				}

				const resolvedId = Number(targetId ?? savedPayload?.backendId);
				if (Number.isFinite(resolvedId) && resolvedId > 0) {
					setResolvedDocumentId(resolvedId);
				}

				setPayload(savedPayload);
				setFields(buildValidationFieldsFromPayload(savedPayload));

				if (savedPayload?.backendId) {
					try {
						const response = await fetchLatestOcrCorrections(savedPayload.backendId);
						const latestCorrections = response?.latest_corrections || {};
						if (isActive && Object.keys(latestCorrections).length > 0) {
							setFields((prev) => mergeBackendCorrectionsIntoFields(prev, latestCorrections));
						}
					} catch {
						// Garder les champs locaux si l'historique des corrections est indisponible.
					}
				}
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
	}, [location.key, location.state?.documentId, queryDocumentId]);

	const previewEntityId = resolvedDocumentId ?? payload?.backendId ?? null;

	const showToast = (type, message) => {
		setToast({ type, message });
		if (timeoutRef.current) {
			window.clearTimeout(timeoutRef.current);
		}
		timeoutRef.current = window.setTimeout(() => setToast(null), 2800);
	};

	const { preview, loading: previewLoading, error: previewError, reload: reloadPreview } = useDocumentFilePreview({
		kind: 'dum',
		entityId: previewEntityId,
		payloadSource: payload?.source,
		fileName: payload?.source?.name || payload?.rawResult?.fichier,
		contentType: payload?.source?.type,
		sourceFileAvailable: payload?.rawResult?.has_source_file,
	});

	const handlePreviewMediaError = () => {
		reloadPreview();
	};

	const displayPreview = preview?.dataUrl ? preview : null;

	const isPdf = Boolean(displayPreview?.type?.toLowerCase().includes('pdf'));

	const modifiedCount = Object.keys(buildModifiedMap(fields)).length;
	const emptyFieldsCount = fields.filter((field) => !String(field?.value ?? '').trim()).length;
	const lowConfidenceCount = fields.filter((field) => typeof field.confidence === 'number' && field.confidence < 80).length;
	const hasValidationPayload = Boolean(payload) && fields.length > 0;

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
		storageKey: 'ocr_validation_payload',
		fields,
		payload,
		setPayload,
		buildModifiedMap,
		enabled: hasValidationPayload,
	});
	const hasBackendLink = Boolean(payload?.backendId);
	const documentLabel = payload?.documentId ?? payload?.backendId ?? 'Document';
	const connectionLabel = hasBackendLink ? `Backend ${payload?.backendId}` : 'Mode local';

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
						backendNewValue: value,
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
				backendOldValue: null,
				backendNewValue: null,
				backendActionType: null,
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

	const persistDumToBackend = async (statut = 'valide') => {
		if (!hasBackendLink) {
			throw new Error('Validation backend impossible: backendId manquant. Recommencez depuis Import/OCR.');
		}
		const backendPayload = buildBackendValidationPayload(fields, payload.backendId, statut);
		await validateOcrDocument(payload.backendId, backendPayload);

		const modifiedFields = buildModifiedMap(fields);
		const finalAudit = {
			...(payload || {}),
			fields,
			modifiedFields,
			validatedAt: new Date().toISOString(),
		};
		localStorage.setItem('ocr_last_validated', JSON.stringify(finalAudit));
		localStorage.setItem(
			'ocr_latest_result',
			JSON.stringify({
				...finalAudit,
				backendId: payload.backendId,
				savedAt: finalAudit.validatedAt,
			})
		);
		return finalAudit;
	};

	const handleFinalValidate = async () => {
		if (!hasBackendLink) {
			showToast('error', 'Validation backend impossible: backendId manquant. Recommencez depuis Import/OCR.');
			return;
		}

		if (isFinalValidating || isCrossVerifying) {
			return;
		}

		setIsFinalValidating(true);
		try {
			await persistDumToBackend('valide');
			setReadyForErp(true);
			showToast(
				'success',
				'DUM validée. Vous pouvez l’envoyer vers l’ERP ou lancer la vérification croisée.'
			);
			setIsFinalValidating(false);
		} catch (error) {
			showToast('error', error?.response?.data?.detail || error?.message || 'Validation finale echouee, veuillez reessayer.');
			setIsFinalValidating(false);
		}
	};

	const goToOcrResults = async () => {
		await syncDumLatestFromValidationPayload();
		const docId = payload?.backendId;
		navigate(docId ? `/ocr-result?documentId=${docId}` : '/ocr-result');
	};

	const handleCancel = () => {
		if (isFinalValidating || isCrossVerifying) {
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
		goToOcrResults();
	};

	const handleCrossVerification = async () => {
		if (!hasBackendLink) {
			showToast('error', 'Enregistrement impossible: backendId manquant.');
			return;
		}
		if (isFinalValidating || isCrossVerifying) {
			return;
		}

		setIsCrossVerifying(true);
		try {
			await persistDumToBackend('valide');
			const declField = fields.find((f) => f.key === 'numero_declaration');
			const dateField = fields.find((f) => f.key === 'date_declaration');
			saveCrossVerificationSession({
				sourceType: 'dum',
				sourceId: payload.backendId,
				sourceNumero: declField?.value || null,
				sourceDate: dateField?.value || null,
				sourceLabel: declField?.value || null,
				sourceFileName: payload?.documentId || displayPreview?.name || `DUM_${payload.backendId}.pdf`,
				sourcePreview: snapshotPreview(displayPreview || payload?.source),
				dumDocumentId: payload.backendId,
				dumPreview: snapshotPreview(displayPreview || payload?.source),
			});
			showToast('success', 'DUM enregistrée. Choisissez la facture à comparer.');
			navigate('/cross-verification');
		} catch (error) {
			showToast(
				'error',
				error?.response?.data?.detail || error?.message || 'Enregistrement echoue.'
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
		const actionMeta = getAuditActionMeta(field.backendActionType);
		const ActionIcon = actionMeta.Icon;
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
						{field.backendActionType && ActionIcon ? (
							<span className={`audit-action-badge ${actionMeta.tone}`}>
								<ActionIcon size={12} />
								{actionMeta.label}
							</span>
						) : null}
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
					<p>Chargement du document…</p>
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
							<p className="validation-kicker">Validation OCR</p>
							<h1>Formulaire de validation OCR</h1>
							<p>Ouvrez cette page depuis la page resultat pour conserver le formulaire et les corrections.</p>
						</div>
					</div>
					<span className="validation-doc-badge">Aucune donnee chargee</span>
				</section>

				<section className="validation-card validation-empty-card">
					<AlertTriangle size={32} />
					<h2>Aucun formulaire a valider</h2>
					<p>
						{initError ||
							'Le payload de validation est vide ou a ete perdu. Retournez a la page resultats OCR puis relancez la validation depuis ce document.'}
					</p>
					<button type="button" className="history-link-btn" onClick={() => navigate('/history')}>
						Retour à l&apos;historique
					</button>
					<button type="button" className="history-link-btn" onClick={goToOcrResults}>
						Résultats OCR
					</button>
				</section>
			</div>
		);
	}

	return (
		<div className="validation-page fade-up">
			{toast ? <div className={`validation-toast ${toast.type}`}>{toast.message}</div> : null}

			<WorkflowBreadcrumb
				workflow="dum"
				current="validation"
				stepToOverrides={{
					ocr: payload?.backendId
						? `/ocr-result?documentId=${payload.backendId}`
						: '/ocr-result',
				}}
			/>

			<section className="validation-header-shell">
				<div className="validation-brand-wrap">
					<div className="validation-brand-mark">EMP</div>
					<div>
						<p className="validation-kicker">Validation DUM</p>
						<h1>Contrôle et correction avant export ERP</h1>
						<p>
							Le formulaire suit la structure de la page résultat et met en avant les champs à corriger.
						</p>
					</div>
				</div>
				<div className="validation-header-meta">
					<span className="validation-doc-badge">
						{documentLabel} · {connectionLabel}
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

			<div className="validation-layout-grid">
				<aside className="validation-preview-column">
					<div className="validation-card preview-card-sticky">
						<div className="preview-card-head">
							<h2>Apercu du document</h2>
							<div className="preview-controls">
								<button type="button" onClick={decreaseZoom} disabled={zoom <= 50} aria-label="Dézoomer">
									<ZoomOut size={16} />
								</button>
								<span>{zoom}%</span>
								<button type="button" onClick={increaseZoom} disabled={zoom >= 200} aria-label="Zoomer">
									<ZoomIn size={16} />
								</button>
								<button type="button" onClick={rotateDocument} aria-label="Rotate">
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
											alt="Document"
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
								<h2>Formulaire de validation DUM</h2>
								<p>
									Le rendu suit la page resultat, avec les champs empiles par section pour rendre les
									corrections plus lisibles.
								</p>
							</div>
							<span>{modifiedCount} modification(s)</span>
						</div>

						<div className="validation-info-banner">
							<AlertTriangle size={16} />
							<p>
								{emptyFieldsCount > 0
									? `${emptyFieldsCount} champ(s) sont vides.`
									: 'Tous les champs éditables contiennent déjà une valeur.'}
								{lowConfidenceCount > 0 ? ` ${lowConfidenceCount} champ(s) ont une confiance faible.` : ''}
							</p>
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
								<p className="validation-empty-state">Aucun champ editable a afficher.</p>
							) : (
								groupedFields.map(([sectionName, sectionFields]) => (
									<div key={sectionName} className="validation-section-block">
										<div className="validation-section-head">
											<p className="validation-section-title">{sectionName}</p>
											<span className="validation-section-count">{sectionFields.length} champ(s)</span>
										</div>
										<div className="validation-section-fields">{sectionFields.map(renderFieldCard)}</div>
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
									disabled={isFinalValidating || isCrossVerifying}
									title="Quitter sans valider vers les résultats OCR"
								>
									Annuler
								</button>
								<button
									type="button"
									className="action-btn reset"
									onClick={handleResetForm}
									disabled={isFinalValidating || isCrossVerifying}
									title="Restaurer les valeurs OCR d'origine"
								>
									<RotateCw size={16} />
									Réinitialiser
								</button>
								<button
									type="button"
									className="action-btn save"
									onClick={handleSaveChanges}
									disabled={isFinalValidating || isCrossVerifying}
									title="Enregistrer le brouillon dans le navigateur"
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
									disabled={isCrossVerifying || isFinalValidating || !hasBackendLink}
									title={
										!hasBackendLink
											? 'Enregistrement backend indisponible sans backendId.'
											: 'Enregistrer puis comparer avec une facture'
									}
								>
									<GitCompare size={16} />
									{isCrossVerifying ? 'Enregistrement…' : 'Vérification croisée'}
								</button>
								<button
									type="button"
									className="action-btn final"
									onClick={handleFinalValidate}
									disabled={isFinalValidating || isCrossVerifying || !hasBackendLink}
									title={
										!hasBackendLink ? 'Validation backend indisponible sans backendId.' : undefined
									}
								>
									<CheckCircle2 size={16} className={isFinalValidating ? 'pulse-check' : ''} />
									{isFinalValidating ? 'Validation…' : 'Valider DUM'}
								</button>
								<ErpExportButton
									kind={ERP_EXPORT.DUM}
									documentId={payload?.backendId}
									dumId={payload?.backendId}
									reference={
										fields.find((f) => f.key === 'numero_declaration')?.value ||
										payload?.documentId
									}
									disabled={!readyForErp || isFinalValidating || isCrossVerifying}
								/>
							</div>
						</div>
						<p className="validation-actions-help">
							<strong>Annuler</strong> : quitter vers les résultats OCR.{' '}
							<strong>Enregistrer brouillon</strong> : sauvegarde locale (auto toutes les 30 s si
							modifications). <strong>Vérification croisée</strong> : enregistre puis ouvre la
							réconciliation facture. <strong>Envoyer DUM vers ERP</strong> : après validation.
						</p>
					</div>
				</section>
			</div>

			<div className="validation-footer-links">
				<button type="button" className="text-link" onClick={goToOcrResults}>
					Retour aux resultats déclaration DUM
				</button>
			</div>
		</div>
	);
}

export default ValidationPage;