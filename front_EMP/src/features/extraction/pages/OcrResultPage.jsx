import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import {
	AlertTriangle,
	FileText,
	Info,
	Maximize2,
	ScanLine,
	Trash2,
	ZoomIn,
	ZoomOut,
} from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { isInvoiceExtractionPayload, looksLikeInvoiceFileName } from '../utils/extractionRouting';
import { DEFAULT_DOCUMENT_ID } from '../utils/ocrFields';
import {
	hydrateDumContextFromApi,
	saveDumValidationPayload,
	syncDumLatestFromValidationPayload,
} from '../utils/documentContextStorage';
import { useDocumentFilePreview } from '../hooks/useDocumentFilePreview';
import './OcrResultPage.css';


const HIDDEN_SECTIONS = new Set(['Metadonnees', 'Qualite OCR', 'Listes']);

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

const toSafeFieldList = (fields) => {
	if (!Array.isArray(fields) || fields.length === 0) {
		return [];
	}
	return fields.map((field) => ({
		...field,
		section: field.section || 'Autres',
		key: field.key || (typeof field.id === 'string' ? field.id : ''),
		isManual: Boolean(field.isManual),
	}));
};

const groupFieldsBySection = (fields) => {
	const groups = new Map();
	fields.forEach((field) => {
		const sectionName = field.section || 'Autres';
		if (!groups.has(sectionName)) {
			groups.set(sectionName, []);
		}
		groups.get(sectionName).push(field);
	});
	return Array.from(groups.entries());
};

function OcrResultPage() {
	const navigate = useNavigate();
	const location = useLocation();
	const [zoom, setZoom] = useState(100);
	const [viewMode, setViewMode] = useState('page');
	const [docSize, setDocSize] = useState(null);
	const [pageFitScale, setPageFitScale] = useState(1);
	const viewportRef = useRef(null);
	const [documentId, setDocumentId] = useState(DEFAULT_DOCUMENT_ID);
	const [backendId, setBackendId] = useState(null);
	const [documentPreview, setDocumentPreview] = useState(null);
	const [docMeta, setDocMeta] = useState(null);
	const [fields, setFields] = useState([]);
	const [modifiedFields, setModifiedFields] = useState({});
	const [focusManualId, setFocusManualId] = useState(null);

	const applyDumPayload = (savedResult, savedPreview) => {
		const isDumPayload =
			savedResult &&
			savedResult.selectedType !== 'invoice' &&
			!isInvoiceExtractionPayload(savedResult);

		if (isDumPayload) {
			setDocumentId(savedResult.documentId || DEFAULT_DOCUMENT_ID);
			setBackendId(savedResult.backendId ?? null);
			setDocumentPreview(savedResult.source || savedPreview);
			setDocMeta(savedResult.rawResult || null);
			setFields(toSafeFieldList(savedResult.fields));
		} else {
			setDocumentId(DEFAULT_DOCUMENT_ID);
			setBackendId(null);
			setDocumentPreview(null);
			setDocMeta(null);
			setFields([]);
		}
		setModifiedFields({});
	};

	useEffect(() => {
		let isActive = true;

		const loadDumResults = async () => {
			const queryId = Number(new URLSearchParams(location.search).get('documentId'));
			const validationPayload = safeJsonParse(localStorage.getItem('ocr_validation_payload'), null);
			const targetId = Number.isFinite(queryId) && queryId > 0
				? queryId
				: validationPayload?.backendId;

			let savedResult = safeJsonParse(localStorage.getItem('ocr_latest_result'), null);
			const savedPreview = safeJsonParse(localStorage.getItem('ocr_uploaded_document'), null);

			if (targetId && Number(savedResult?.backendId) !== Number(targetId)) {
				if (Number(validationPayload?.backendId) === Number(targetId)) {
					await syncDumLatestFromValidationPayload();
					savedResult = safeJsonParse(localStorage.getItem('ocr_latest_result'), null);
				} else {
					try {
						await hydrateDumContextFromApi(targetId);
						if (!isActive) {
							return;
						}
						savedResult = safeJsonParse(localStorage.getItem('ocr_latest_result'), null);
					} catch {
						if (!isActive) {
							return;
						}
					}
				}
			}

			if (!isActive) {
				return;
			}
			applyDumPayload(savedResult, savedPreview);
		};

		loadDumResults();

		return () => {
			isActive = false;
		};
	}, [location.pathname, location.search, location.key]);

	const { preview: remotePreview, loading: previewLoading, error: previewError } =
		useDocumentFilePreview({
			kind: 'dum',
			entityId: backendId,
			payloadSource: documentPreview,
			fileName: documentPreview?.name || docMeta?.fichier,
			contentType: documentPreview?.type,
			dossier: docMeta?.dossier,
			sourceFileAvailable: docMeta?.has_source_file,
		});

	const displayPreview = documentPreview?.dataUrl ? documentPreview : remotePreview;
	const hasPreview = Boolean(displayPreview?.dataUrl);
	const isPdf = hasPreview && displayPreview?.type?.toLowerCase().includes('pdf');

	const handleZoomIn = () => {
		setZoom((prev) => Math.min(prev + 25, 200));
	};

	const handleZoomOut = () => {
		setZoom((prev) => Math.max(prev - 25, 50));
	};

	const updatePageFit = useCallback(() => {
		if (viewMode !== 'page' || isPdf || !viewportRef.current || !docSize) {
			return;
		}
		const viewport = viewportRef.current;
		const padding = 36;
		const availableWidth = viewport.clientWidth - padding;
		const availableHeight = viewport.clientHeight - padding;
		if (availableWidth <= 0 || availableHeight <= 0) {
			return;
		}
		const scale = Math.min(
			availableWidth / docSize.width,
			availableHeight / docSize.height,
			1,
		);
		setPageFitScale(scale);
	}, [viewMode, isPdf, docSize]);

	useLayoutEffect(() => {
		updatePageFit();
	}, [updatePageFit, zoom]);

	useEffect(() => {
		const onResize = () => updatePageFit();
		window.addEventListener('resize', onResize);
		return () => window.removeEventListener('resize', onResize);
	}, [updatePageFit]);

	useEffect(() => {
		setDocSize(null);
		setPageFitScale(1);
	}, [documentPreview?.dataUrl]);

	useEffect(() => {
		const image = viewportRef.current?.querySelector('.ocr-doc-image');
		if (image?.complete && image.naturalWidth > 0) {
			setDocSize({ width: image.naturalWidth, height: image.naturalHeight });
		}
	}, [documentPreview?.dataUrl]);

	const handleImageLoad = (event) => {
		const image = event.currentTarget;
		if (!image.naturalWidth || !image.naturalHeight) {
			return;
		}
		setDocSize({ width: image.naturalWidth, height: image.naturalHeight });
	};

	const zoomFactor = zoom / 100;
	const isPageFitCentered = viewMode === 'page' && zoom === 100;

	const imageStyle = useMemo(() => {
		if (!docSize) {
			return { width: '100%', height: 'auto' };
		}
		if (viewMode === 'width') {
			return {
				width: `${100 * zoomFactor}%`,
				height: 'auto',
				maxWidth: 'none',
			};
		}
		return {
			width: `${Math.round(docSize.width * pageFitScale * zoomFactor)}px`,
			height: 'auto',
			maxWidth: 'none',
		};
	}, [docSize, viewMode, zoomFactor, pageFitScale]);

	const handleFieldChange = (id, key, value) => {
		setFields((prev) =>
			prev.map((field) => {
				if (field.id !== id) {
					return field;
				}

				const next = {
					...field,
					[key]: value,
				};

				if (key === 'value' && field.hasError && String(value).trim().length > 0) {
					next.hasError = false;
				}

				return next;
			})
		);

		setModifiedFields((prev) => ({
			...prev,
			[id]: {
				...(prev[id] || {}),
				[key]: value,
			},
		}));
	};

	const removeManualField = (id) => {
		setFields((prev) => prev.filter((field) => field.id !== id));
		setModifiedFields((prev) => {
			const next = { ...prev };
			delete next[id];
			return next;
		});
	};

	const hasModifications = Object.keys(modifiedFields).length > 0;
	const hasNoFields = fields.length === 0;
	// Comme la facture : validation possible sans modification prealable (corrections sur /validation).
	const disableValidation = hasNoFields;
	const groupedFields = groupFieldsBySection(fields).filter(
		([sectionName]) => !HIDDEN_SECTIONS.has(sectionName)
	);
	const hasPendingChanges = hasModifications;

	const handleValidate = () => {
		const previewForValidation = displayPreview?.dataUrl
			? displayPreview
			: documentPreview?.dataUrl
				? documentPreview
				: remotePreview?.dataUrl
					? remotePreview
					: null;
		const { ok } = saveDumValidationPayload({
			documentId,
			backendId,
			fields,
			modifiedFields,
			preview: previewForValidation,
			rawResult: docMeta,
		});
		if (!ok) {
			window.alert(
				'Les champs ont été préparés mais le brouillon local est trop volumineux. L\'aperçu sera rechargé depuis le serveur sur la page validation.'
			);
		}
		navigate('/validation');
	};

	const resetOcrResult = () => {
		localStorage.removeItem('ocr_validation_payload');
		localStorage.removeItem('ocr_latest_result');
		localStorage.removeItem('ocr_uploaded_document');
		setDocumentId(DEFAULT_DOCUMENT_ID);
		setBackendId(null);
		setDocumentPreview(null);
		setFields([]);
		setModifiedFields({});
		setFocusManualId(null);
		setZoom(100);
	};

	const handleCancel = () => {
		if (hasPendingChanges) {
			const confirmed = window.confirm('Voulez-vous annuler les modifications et vider les donnees affichees ?');
			if (!confirmed) {
				return;
			}
		}

		resetOcrResult();
	};

	return (
		<div className="ocr-result-page fade-up">
			<section className="ocr-result-header">
				<div>
					<p className="ocr-result-kicker">OCR</p>
					<h1>Resultats d&apos;Extraction Déclaration DUM</h1>
				</div>
				<span className="ocr-doc-badge">{documentId}</span>
			</section>

			<div className="ocr-result-grid">
				<section className="ocr-panel ocr-preview-panel">
					<header className="ocr-preview-head">
						<div className="ocr-preview-head-icon">
							<FileText size={20} />
						</div>
						<div>
							<h2>Aperçu du Document Original</h2>
							<p>Zoomez puis faites défiler pour voir tout le document</p>
						</div>
					</header>

					<div className="ocr-doc-viewer">
						<div
							ref={viewportRef}
							className={`ocr-doc-viewer-body ${isPageFitCentered ? 'ocr-doc-viewer-body--centered' : ''}`}
						>
							{hasPreview ? (
								isPdf ? (
									<iframe
										title="Document PDF"
										src={displayPreview.dataUrl}
										className="ocr-doc-pdf"
									/>
								) : (
									<div className="ocr-doc-canvas">
										<img
											src={displayPreview.dataUrl}
											alt="Document OCR"
											className="ocr-doc-image"
											style={imageStyle}
											onLoad={handleImageLoad}
											draggable={false}
										/>
									</div>
								)
							) : (
								<div className="ocr-preview-placeholder">
									<FileText size={26} />
									<p>
										{previewLoading
											? 'Chargement de l\u2019aperçu depuis la GED…'
											: 'Aucun document chargé'}
									</p>
									{previewError ? <p className="preview-placeholder-error">{previewError}</p> : null}
								</div>
							)}
						</div>

						{hasPreview && (
							<div className="ocr-doc-toolbar" role="toolbar" aria-label="Contrôles du document">
								<button
									type="button"
									className={`ocr-doc-mode-btn ${viewMode === 'page' ? 'is-active' : ''}`}
									onClick={() => {
										setViewMode('page');
										setZoom(100);
									}}
									aria-pressed={viewMode === 'page'}
								>
									<Maximize2 size={15} />
									Page
								</button>
								<button
									type="button"
									className={`ocr-doc-mode-btn ${viewMode === 'width' ? 'is-active' : ''}`}
									onClick={() => {
										setViewMode('width');
										setZoom(100);
									}}
									aria-pressed={viewMode === 'width'}
									disabled={isPdf}
								>
									<ScanLine size={15} />
									Largeur
								</button>
								<span className="ocr-doc-toolbar-sep" aria-hidden="true" />
								<button
									type="button"
									onClick={handleZoomOut}
									className="ocr-doc-zoom-btn"
									disabled={zoom <= 50}
									aria-label="Dézoomer"
								>
									<ZoomOut size={16} />
								</button>
								<button
									type="button"
									className="ocr-doc-zoom-value"
									onClick={() => setZoom(100)}
									aria-label="Réinitialiser le zoom"
								>
									{zoom}%
								</button>
								<button
									type="button"
									onClick={handleZoomIn}
									className="ocr-doc-zoom-btn"
									disabled={zoom >= 200}
									aria-label="Zoomer"
								>
									<ZoomIn size={16} />
								</button>
							</div>
						)}
					</div>
				</section>

				<section className="ocr-panel ocr-data-panel">
					<header className="ocr-panel-head data-head">
						<div>
							<h2>Donnees Extraites</h2>
							<p>Verifiez et corrigez les donnees extraites</p>
						</div>
						<span className="ocr-badge">OCR</span>
					</header>

					{displayPreview?.name && looksLikeInvoiceFileName(displayPreview.name) ? (
						<div className="ocr-info-banner ocr-info-banner--warning">
							<AlertTriangle size={16} />
							<p>
								Ce document ressemble a une <strong>facture</strong>, mais le formulaire affiche est celui
								d&apos;une DUM. Reimportez depuis Import en choisissant{' '}
								<strong>Facture commerciale</strong>, ou ouvrez{' '}
								<Link to="/invoice-ocr-result">Resultats facture</Link>.
							</p>
						</div>
					) : null}

					<div className="ocr-info-banner">
						<Info size={16} />
						<p>
							Seuls les champs detectes sur la DUM sont affiches. Corrigez puis validez depuis le formulaire de validation.
						</p>
					</div>

					<div className="ocr-field-list">
						{groupedFields.length === 0 ? (
							<div className="ocr-empty-state">
								<p>Aucune extraction DUM enregistree.</p>
								<p className="ocr-empty-hint">
									Importez une declaration depuis la page Import, ou consultez{' '}
									<Link to="/invoice-ocr-result">Resultats facture</Link> si vous avez extrait une facture.
								</p>
							</div>
						) : groupedFields.map(([sectionName, sectionFields]) => (
							<div key={sectionName} className="ocr-section-block">
								<p className="ocr-section-title">{sectionName}</p>
								{sectionFields.map((field) => {
									const isModified = Boolean(modifiedFields[field.id]);
									const confidenceIsHigh = typeof field.confidence === 'number' && field.confidence >= 80;

									return (
										<div
											key={field.id}
											className={`ocr-field-card ${field.hasError ? 'has-error' : ''} ${isModified ? 'is-modified' : ''}`}
										>
											<div className="ocr-field-head">
												{field.isManual ? (
													<input
														type="text"
														value={field.label}
														autoFocus={focusManualId === field.id}
														onFocus={() => setFocusManualId(field.id)}
														onBlur={() => setFocusManualId(null)}
														onChange={(event) => handleFieldChange(field.id, 'label', event.target.value)}
														placeholder='ex: Numero TVA, Code HS...'
														className="ocr-manual-label"
													/>
												) : (
													<label>{field.label}</label>
												)}

												<div className="ocr-field-badges">
													{typeof field.confidence === 'number' && (
														<span className={`ocr-confidence ${confidenceIsHigh ? 'high' : 'low'}`}>
															{confidenceIsHigh ? null : <AlertTriangle size={12} />}
															{field.confidence}%
														</span>
													)}
													{field.isManual && <span className="ocr-manual-badge">Ajoute manuellement</span>}
													{field.isManual && (
														<button
															type="button"
															onClick={() => removeManualField(field.id)}
															className="ocr-remove-field"
															aria-label="Supprimer ce champ"
														>
															<Trash2 size={15} />
														</button>
													)}
												</div>
											</div>

											<input
												type="text"
												value={field.value}
												onChange={(event) => handleFieldChange(field.id, 'value', event.target.value)}
												placeholder='Entrez la valeur...'
												className="ocr-field-input"
											/>
										</div>
									);
								})}
							</div>
						))}
					</div>

					<div className="ocr-action-row">
						<button type="button" className="ocr-cancel-btn" onClick={handleCancel}>
							Annuler
						</button>
						<button
							type="button"
							className="ocr-validate-btn"
							onClick={handleValidate}
							disabled={disableValidation}
						>
							Valider les données de déclaration DUM 
						</button>
					</div>
				</section>
			</div>
		</div>
	);
}

export default OcrResultPage;
