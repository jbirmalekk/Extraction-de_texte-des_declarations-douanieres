import { useEffect, useMemo, useRef, useState } from 'react';
import {
	AlertTriangle,
	CheckCircle2,
	FileText,
	Pencil,
	Plus,
	RotateCw,
	Save,
	Trash2,
	ZoomIn,
	ZoomOut,
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { fetchLatestOcrCorrections, validateOcrDocument } from '../services/ocrService';
import { buildBackendValidationPayload } from '../utils/ocrFields';
import { useAuth } from '../hooks/useAuth';
import './ValidationPage.css';

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

function ValidationPage() {
	const navigate = useNavigate();
	const { user } = useAuth();
	const [payload, setPayload] = useState(null);
	const [fields, setFields] = useState([]);
	const [toast, setToast] = useState(null);
	const [isFinalValidating, setIsFinalValidating] = useState(false);
	const [zoom, setZoom] = useState(100);
	const [rotation, setRotation] = useState(0);
	const timeoutRef = useRef(null);

	useEffect(() => {
		let isActive = true;
		const savedPayload = safeJsonParse(localStorage.getItem('ocr_validation_payload'), null);
		setPayload(savedPayload);
		setFields(buildValidationFieldsFromPayload(savedPayload));

		const hydrateBackendCorrections = async () => {
			if (!savedPayload?.backendId) {
				return;
			}

			try {
				const response = await fetchLatestOcrCorrections(savedPayload.backendId);
				const latestCorrections = response?.latest_corrections || {};
				if (!isActive || Object.keys(latestCorrections).length === 0) {
					return;
				}

				setFields((prev) => mergeBackendCorrectionsIntoFields(prev, latestCorrections));
			} catch (_error) {
				// Keep local experience even if history hydration fails.
			}
		};

		hydrateBackendCorrections();

		return () => {
			isActive = false;
			if (timeoutRef.current) {
				window.clearTimeout(timeoutRef.current);
			}
		};
	}, []);

	const showToast = (type, message) => {
		setToast({ type, message });
		if (timeoutRef.current) {
			window.clearTimeout(timeoutRef.current);
		}
		timeoutRef.current = window.setTimeout(() => setToast(null), 2800);
	};

	const preview = useMemo(() => {
		if (payload?.source?.dataUrl) {
			return payload.source;
		}
		return safeJsonParse(localStorage.getItem('ocr_uploaded_document'), null);
	}, [payload]);

	const isPdf = Boolean(preview?.type?.toLowerCase().includes('pdf'));

	const groupedFields = useMemo(() => {
		const groups = new Map();
		fields.forEach((field) => {
			const sectionName = field?.section || 'Autres';
			if (NON_EDITABLE_SECTIONS.has(sectionName)) {
				return;
			}
			if (!groups.has(sectionName)) {
				groups.set(sectionName, []);
			}
			groups.get(sectionName).push(field);
		});
		return Array.from(groups.entries());
	}, [fields]);

	const modifiedCount = Object.keys(buildModifiedMap(fields)).length;
	const emptyFieldsCount = fields.filter((field) => !String(field?.value ?? '').trim()).length;
	const lowConfidenceCount = fields.filter((field) => typeof field.confidence === 'number' && field.confidence < 80).length;
	const hasValidationPayload = Boolean(payload) && fields.length > 0;
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
		showToast('info', 'Formulaire reinitialise aux donnees OCR originales.');
	};

	const handleSaveChanges = () => {
		const modifiedFields = buildModifiedMap(fields);
		const updatedPayload = {
			...(payload || {}),
			fields,
			modifiedFields,
			savedAt: new Date().toISOString(),
		};
		setPayload(updatedPayload);
		localStorage.setItem('ocr_validation_payload', JSON.stringify(updatedPayload));
		showToast('success', 'Modifications sauvegardees.');
	};

	const handleFinalValidate = async () => {
		if (!hasBackendLink) {
			showToast('error', 'Validation backend impossible: backendId manquant. Recommencez depuis Import/OCR.');
			return;
		}

		if (isFinalValidating) {
			return;
		}

		setIsFinalValidating(true);
		try {
			if (payload?.backendId) {
				const backendPayload = buildBackendValidationPayload(fields, payload.backendId, 'valide');
				await validateOcrDocument(payload.backendId, backendPayload);
			}

			const modifiedFields = buildModifiedMap(fields);
			const finalAudit = {
				...(payload || {}),
				fields,
				modifiedFields,
				validatedAt: new Date().toISOString(),
			};
			localStorage.setItem('ocr_last_validated', JSON.stringify(finalAudit));
			showToast('success', 'Document valide avec succes ! Pret pour l\'exportation ERP.');

			timeoutRef.current = window.setTimeout(() => {
				navigate('/erp-success');
			}, 1500);
		} catch (error) {
			showToast('error', error?.response?.data?.detail || 'Validation finale echouee, veuillez reessayer.');
			setIsFinalValidating(false);
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
					{field.backendOldValue !== null || field.backendNewValue !== null ? (
						<p>
							<span>Correction backend</span>
							{String(field.backendOldValue ?? '—')} → {String(field.backendNewValue ?? '—')}
						</p>
					) : null}
				</div>
			</div>
		);
	};

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
						Le payload de validation est vide ou a ete perdu. Retournez a la page resultats OCR
						puis relancez la validation depuis ce document.
					</p>
					<Link to="/ocr-result" className="history-link-btn">
						Retour aux resultats OCR
					</Link>
				</section>
			</div>
		);
	}

	return (
		<div className="validation-page fade-up">
			{toast ? <div className={`validation-toast ${toast.type}`}>{toast.message}</div> : null}

			<section className="validation-header-shell">
				<div className="validation-brand-wrap">
					<div className="validation-brand-mark">EMP</div>
					<div>
						<p className="validation-kicker">Validation OCR</p>
						<h1>Controle et correction avant export ERP</h1>
						<p>
							Le formulaire suit la structure de la page resultat et met en avant les champs a corriger.
						</p>
					</div>
				</div>
				<span className="validation-doc-badge">
					{documentLabel} · {connectionLabel}
				</span>
			</section>

			<div className="validation-layout-grid">
				<aside className="validation-preview-column">
					<div className="validation-card preview-card-sticky">
						<div className="preview-card-head">
							<h2>Apercu du document</h2>
							<div className="preview-controls">
								<button type="button" onClick={decreaseZoom} disabled={zoom <= 50} aria-label="Zoom out">
									<ZoomOut size={16} />
								</button>
								<span>{zoom}%</span>
								<button type="button" onClick={increaseZoom} disabled={zoom >= 200} aria-label="Zoom in">
									<ZoomIn size={16} />
								</button>
								<button type="button" onClick={rotateDocument} aria-label="Rotate">
									<RotateCw size={16} />
								</button>
							</div>
						</div>

						<div className="preview-viewport" onWheel={handlePreviewWheel}>
							<div
								className="preview-transform-layer"
								style={{ transform: `scale(${zoom / 100}) rotate(${rotation}deg)` }}
							>
								{preview?.dataUrl ? (
									isPdf ? (
										<iframe title="Document PDF" src={preview.dataUrl} className="preview-pdf" />
									) : (
										<img src={preview.dataUrl} alt="Document" className="preview-image" />
									)
								) : (
									<div className="preview-placeholder">
										<FileText size={52} />
										<p>Apercu du document</p>
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
								<h2>Formulaire de validation OCR</h2>
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
									: 'Tous les champs editables contiennent deja une valeur.'}
								{lowConfidenceCount > 0 ? ` ${lowConfidenceCount} champ(s) ont une confiance faible.` : ''}
							</p>
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
							<button type="button" className="action-btn reset" onClick={handleResetForm}>
								↻ Reset Form
							</button>
							<button type="button" className="action-btn save" onClick={handleSaveChanges}>
								<Save size={16} />
								Save Changes
							</button>
							<button
								type="button"
								className="action-btn final"
								onClick={handleFinalValidate}
								disabled={isFinalValidating || !hasBackendLink}
								title={
									!hasBackendLink ? 'Validation backend indisponible sans backendId.' : undefined
								}
							>
								<CheckCircle2 size={16} className={isFinalValidating ? 'pulse-check' : ''} />
								{isFinalValidating ? 'Validation...' : '✓ Final Validate'}
							</button>
						</div>
					</div>
				</section>
			</div>

			<div className="validation-footer-links">
				<Link to="/ocr-result">Retour aux resultats OCR</Link>
			</div>
		</div>
	);
}

export default ValidationPage;