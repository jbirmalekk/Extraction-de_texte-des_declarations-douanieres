import { useEffect, useState } from 'react';
import {
	AlertTriangle,
	FileText,
	Info,
	Trash2,
	ZoomIn,
	ZoomOut,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { DEFAULT_DOCUMENT_ID } from '../utils/ocrFields';
import './OcrResultPage.css';

const OVERLAY_ZONES = [
	{ id: 'zone-1', label: 'N Declaration', top: '14%', left: '8%', width: '42%', height: '14%' },
	{ id: 'zone-2', label: 'Date', top: '32%', left: '56%', width: '30%', height: '12%' },
	{ id: 'zone-3', label: 'Montant', top: '52%', left: '14%', width: '34%', height: '16%' },
	{ id: 'zone-4', label: 'Code HS', top: '72%', left: '48%', width: '36%', height: '14%' },
];

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
	const [zoom, setZoom] = useState(100);
	const [documentId, setDocumentId] = useState(DEFAULT_DOCUMENT_ID);
	const [backendId, setBackendId] = useState(null);
	const [documentPreview, setDocumentPreview] = useState(null);
	const [fields, setFields] = useState([]);
	const [modifiedFields, setModifiedFields] = useState({});
	const [focusManualId, setFocusManualId] = useState(null);

	useEffect(() => {
		const savedResult = safeJsonParse(localStorage.getItem('ocr_latest_result'), null);
		const savedPreview = safeJsonParse(localStorage.getItem('ocr_uploaded_document'), null);

		if (savedResult) {
			if (savedResult.documentId) {
				setDocumentId(savedResult.documentId);
			}
			if (savedResult.backendId) {
				setBackendId(savedResult.backendId);
			}
			if (savedResult.source) {
				setDocumentPreview(savedResult.source);
			} else if (savedPreview) {
				setDocumentPreview(savedPreview);
			}
			setFields(toSafeFieldList(savedResult.fields));
		} else {
			setFields([]);
			if (savedPreview) {
				setDocumentPreview(savedPreview);
			}
		}
	}, []);

	const hasPreview = Boolean(documentPreview?.dataUrl);
	const isPdf = hasPreview && documentPreview?.type?.toLowerCase().includes('pdf');

	const handleZoomIn = () => {
		setZoom((prev) => Math.min(prev + 25, 200));
	};

	const handleZoomOut = () => {
		setZoom((prev) => Math.max(prev - 25, 50));
	};

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

	const hasUnresolvedErrors = fields.some((field) => field.hasError && !modifiedFields[field.id]);
	const hasModifications = Object.keys(modifiedFields).length > 0;
	const hasNoFields = fields.length === 0;
	const disableValidation = hasNoFields || (!hasModifications && hasUnresolvedErrors);
	const groupedFields = groupFieldsBySection(fields).filter(
		([sectionName]) => !HIDDEN_SECTIONS.has(sectionName)
	);
	const hasPendingChanges = hasModifications;

	const handleValidate = () => {
		const payload = {
			documentId,
			backendId,
			fields,
			modifiedFields,
			savedAt: new Date().toISOString(),
		};
		localStorage.setItem('ocr_validation_payload', JSON.stringify(payload));
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
					<h1>Resultats d&apos;Extraction OCR</h1>
				</div>
				<span className="ocr-doc-badge">{documentId}</span>
			</section>

			<div className="ocr-result-grid">
				<section className="ocr-panel ocr-preview-panel">
					<header className="ocr-panel-head">
						<h2>Apercu du Document Original</h2>
					</header>

					<div className="ocr-preview-viewport">
						<div
							className="ocr-preview-canvas"
							style={{ transform: `scale(${zoom / 100})` }}
						>
							{documentPreview?.dataUrl ? (
								isPdf ? (
									<iframe
										title="Document PDF"
										src={documentPreview.dataUrl}
										className="ocr-preview-pdf"
									/>
								) : (
									<img
										src={documentPreview.dataUrl}
										alt="Document OCR"
										className="ocr-preview-image"
									/>
								)
							) : (
								<div className="ocr-preview-placeholder">
									<FileText size={26} />
									<p>Aucun document charge</p>
								</div>
							)}

							{hasPreview && !isPdf && (
								<div className="ocr-zone-overlay" aria-hidden="true">
									{OVERLAY_ZONES.map((zone) => (
										<div
											key={zone.id}
											className="ocr-zone-box"
											style={{
												top: zone.top,
												left: zone.left,
												width: zone.width,
												height: zone.height,
											}}
										>
											<span>{zone.label}</span>
										</div>
									))}
								</div>
							)}
						</div>
					</div>

					<div className="ocr-zoom-controls">
						<button type="button" onClick={handleZoomOut} className="ocr-zoom-btn" aria-label="Zoom out">
							<ZoomOut size={16} />
						</button>
						<span>{zoom}%</span>
						<button type="button" onClick={handleZoomIn} className="ocr-zoom-btn" aria-label="Zoom in">
							<ZoomIn size={16} />
						</button>
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

					<div className="ocr-info-banner">
						<Info size={16} />
						<p>
							Le modele OCR peut parfois omettre certains champs. Corrigez les valeurs directement
							dans la liste ci-dessous.
						</p>
					</div>

					<div className="ocr-field-list">
						{groupedFields.length === 0 ? (
							<p>Aucune donnee a afficher.</p>
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
							Valider les donnees
						</button>
					</div>
				</section>
			</div>
		</div>
	);
}

export default OcrResultPage;
