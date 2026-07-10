import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, FileBadge2, ShieldCheck, Sparkles, Upload } from 'lucide-react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import DropZone from '../components/Import/DropZone';
import FilePreview from '../components/Import/FilePreview';
import FileTypeSelector from '../components/Import/FileTypeSelector';
import ImageCropper from '../components/Import/ImageCropper';
import UploadProgress from '../components/Import/UploadProgress';
import { createInvoiceFromUpload, fetchInvoiceById } from '../services/invoiceApi';
import { extractOcrDocument } from '../services/ocrService';
import { mapInvoiceBackendToFields } from '../utils/invoiceFields';
import { DEFAULT_DOCUMENT_ID, mapBackendResultToFields } from '../utils/ocrFields';
import {
	looksLikeDumFileName,
	looksLikeInvoiceFileName,
	setLastExtractionType,
} from '../utils/extractionRouting';
import {
	consumeCrossVerifyImportReturn,
	getCrossVerificationSession,
	markCrossVerifyImportReturn,
	updateCrossVerificationSession,
} from '../utils/crossVerificationSession';
import { useAuth } from '../hooks/useAuth';
import { writeSessionDocumentPreview } from '../utils/documentPreviewCache';

const fileTypeOptions = [
	{
		id: 'declaration',
		label: 'Declaration douaniere',
		description: 'Extrait les codes, taxes et champs reglementaires',
		badge: 'Recommande',
	},
	{
		id: 'invoice',
		label: 'Facture commerciale',
		description: 'Capture vendeur, client et details de lignes',
		badge: 'Nouveau',
	},
	
];

const readFileAsDataUrl = (file) =>
	new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(reader.result);
		reader.onerror = () => reject(new Error('Impossible de lire le document.'));
		reader.readAsDataURL(file);
	});

const RAW_RESULT_STORAGE_EXCLUDE = new Set(['texte_brut', 'texte_nettoye']);

const buildStoredRawResult = (result) => {
	if (!result || typeof result !== 'object') {
		return result;
	}

	return Object.fromEntries(
		Object.entries(result).filter(([key]) => !RAW_RESULT_STORAGE_EXCLUDE.has(key))
	);
};

const persistJsonSafely = (key, payload) => {
	try {
		localStorage.setItem(key, JSON.stringify(payload));
		return true;
	} catch (error) {
		console.warn(`Impossible de sauvegarder ${key} dans localStorage`, error);
		return false;
	}
};

const persistBatchItemSnapshot = (index, payload) => {
	try {
		sessionStorage.setItem(`ocr_batch_item_${index}`, JSON.stringify(payload));
		return true;
	} catch (error) {
		console.warn(`Impossible de sauvegarder le lot #${index}`, error);
		return false;
	}
};

const clearBatchItemSnapshots = (count) => {
	for (let i = 0; i < count; i += 1) {
		sessionStorage.removeItem(`ocr_batch_item_${i}`);
	}
};

const clearPreviousOcrDraft = () => {
	localStorage.removeItem('ocr_validation_payload');
	localStorage.removeItem('ocr_latest_result');
	localStorage.removeItem('ocr_uploaded_document');
};

const clearPreviousInvoiceDraft = () => {
	localStorage.removeItem('invoice_validation_payload');
	localStorage.removeItem('invoice_latest_result');
	localStorage.removeItem('invoice_uploaded_document');
};

const persistDocumentPreview = (source) => {
	const docId = source?.documentId ?? source?.backendId;
	if (docId != null) {
		writeSessionDocumentPreview('dum', docId, source);
	}
	if (persistJsonSafely('ocr_uploaded_document', source)) {
		return;
	}
	const { dataUrl: _dataUrl, ...sourceMeta } = source;
	persistJsonSafely('ocr_uploaded_document', sourceMeta);
};

const fileFingerprint = (file) => `${file.name}::${file.size}::${file.lastModified}`;

const mergeSelectedFiles = (existing, incoming) => {
	const map = new Map();
	existing.forEach((file) => map.set(fileFingerprint(file), file));
	incoming.forEach((file) => map.set(fileFingerprint(file), file));
	return Array.from(map.values());
};

const formatApiDetail = (detail) => {
	if (!detail) {
		return null;
	}
	if (typeof detail === 'string') {
		return detail;
	}
	if (typeof detail === 'object') {
		return [detail.message, detail.hint, detail.error].filter(Boolean).join(' — ');
	}
	return String(detail);
};

const getUploadErrorMessage = (error, isInvoice) => {
	const detail = formatApiDetail(error?.response?.data?.detail);
	if (error?.code === 'ECONNABORTED') {
		return isInvoice
			? "Delai depasse lors de l'extraction facture. Reessayez dans quelques instants."
			: "Delai depasse lors de l'extraction DUM. Reessayez dans quelques instants.";
	}
	if (error?.message === 'Network Error' || !error?.response) {
		return (
			'Le serveur OCR a echoue (erreur reseau ou 500). Verifiez que back_EMP tourne sur le port 8000 ' +
			'et que Tesseract OCR est installe (voir logs uvicorn).'
		);
	}
	return (
		detail ||
		error?.response?.data?.message ||
		error?.message ||
		"L'extraction a echoue."
	);
};

const buildDocumentId = (backendResult) => {
	if (backendResult?.numero_declaration) {
		return backendResult.numero_declaration;
	}
	if (backendResult?.id) {
		const year = new Date().getFullYear();
		const serial = String(backendResult.id).padStart(4, '0');
		return `INV-${year}-${serial}`;
	}
	return DEFAULT_DOCUMENT_ID;
};

function ImportPage() {
	const navigate = useNavigate();
	const [searchParams] = useSearchParams();
	const { user } = useAuth();
	const returnToCrossVerify = searchParams.get('returnTo') === 'cross-verification';
	const [selectedFiles, setSelectedFiles] = useState([]);
	const [selectedType, setSelectedType] = useState(fileTypeOptions[0].id);
	const [uploadStatus, setUploadStatus] = useState('idle');
	const [uploadProgress, setUploadProgress] = useState(0);
	const [uploadDetail, setUploadDetail] = useState('');
	const [errorMessage, setErrorMessage] = useState('');
	const [activeCropKey, setActiveCropKey] = useState(null);
	const [activeCropImageUrl, setActiveCropImageUrl] = useState('');
	const [croppedFilesByKey, setCroppedFilesByKey] = useState({});

	const croppedFileKeys = Object.keys(croppedFilesByKey);
	const activeCropFile = selectedFiles.find((file) => fileFingerprint(file) === activeCropKey);

	useEffect(() => {
		let objectUrl = '';
		if (activeCropKey && activeCropFile?.type?.startsWith('image/')) {
			objectUrl = URL.createObjectURL(activeCropFile);
			setActiveCropImageUrl(objectUrl);
		} else {
			setActiveCropImageUrl('');
		}
		return () => {
			if (objectUrl) {
				URL.revokeObjectURL(objectUrl);
			}
		};
	}, [activeCropKey, activeCropFile]);

	useEffect(() => {
		const docType = searchParams.get('docType');
		if (docType === 'invoice' || docType === 'declaration') {
			setSelectedType(docType);
		}
		if (returnToCrossVerify) {
			const partnerKind = docType === 'invoice' ? 'invoice' : 'dum';
			markCrossVerifyImportReturn(partnerKind);
		}
	}, [searchParams, returnToCrossVerify]);

	const handleFileDrop = (files) => {
		const normalizedFiles = Array.isArray(files) ? files : files ? [files] : [];
		if (!normalizedFiles.length) {
			return;
		}
		const firstName = normalizedFiles[0]?.name || '';
		if (looksLikeInvoiceFileName(firstName) && !looksLikeDumFileName(firstName)) {
			setSelectedType('invoice');
		} else if (looksLikeDumFileName(firstName) && !looksLikeInvoiceFileName(firstName)) {
			setSelectedType('declaration');
		}
		setSelectedFiles((prev) => mergeSelectedFiles(prev, normalizedFiles));
		setUploadStatus('ready');
		setUploadProgress(0);
		setErrorMessage('');
	};

	const handleSelectFileForCrop = (index) => {
		const file = selectedFiles[index];
		if (!file) {
			return;
		}
		if (!file.type?.startsWith('image/')) {
			setErrorMessage('Le cadrage est disponible uniquement pour les images (JPG, PNG).');
			return;
		}
		setErrorMessage('');
		setActiveCropKey(fileFingerprint(file));
	};

	const handleCropApplied = ({ croppedFile: nextCroppedFile, error }) => {
		if (error) {
			setErrorMessage(error.message || "Impossible d'appliquer le decoupage.");
			return;
		}
		if (!nextCroppedFile || !activeCropKey) {
			return;
		}
		setCroppedFilesByKey((prev) => ({
			...prev,
			[activeCropKey]: nextCroppedFile,
		}));
		setErrorMessage('');
	};

	const handleRemoveFile = () => {
		setSelectedFiles([]);
		setActiveCropKey(null);
		setCroppedFilesByKey({});
		setUploadStatus('idle');
		setUploadProgress(0);
		setErrorMessage('');
	};

	const handleRemoveFileAt = (indexToRemove) => {
		const removed = selectedFiles[indexToRemove];
		const removedKey = removed ? fileFingerprint(removed) : null;

		setSelectedFiles((prev) => prev.filter((_, idx) => idx !== indexToRemove));

		if (removedKey) {
			setCroppedFilesByKey((prev) => {
				const next = { ...prev };
				delete next[removedKey];
				return next;
			});
			if (activeCropKey === removedKey) {
				setActiveCropKey(null);
			}
		}

		setUploadStatus(selectedFiles.length > 1 ? 'ready' : 'idle');
	};

	const startUpload = async () => {
		if (!selectedFiles.length) {
			return;
		}
		if (returnToCrossVerify && selectedFiles.length > 1) {
			setErrorMessage('La réconciliation accepte un seul document à la fois.');
			return;
		}

		let uploadDocumentType = selectedType;
		const primaryFile = selectedFiles[0];
		if (
			uploadDocumentType === 'declaration' &&
			looksLikeInvoiceFileName(primaryFile?.name) &&
			!looksLikeDumFileName(primaryFile?.name)
		) {
			const useInvoice = window.confirm(
				'Ce fichier ressemble a une facture commerciale.\n\n' +
					'OK = extraire en mode Facture (formulaire facture)\n' +
					'Annuler = garder le mode Declaration DUM'
			);
			if (useInvoice) {
				uploadDocumentType = 'invoice';
				setSelectedType('invoice');
			}
		}

		setUploadStatus('uploading');
		setUploadProgress(0);
		setUploadDetail('');
		setErrorMessage('');

		try {
			const isSingleUpload = selectedFiles.length === 1;
			const filesToProcess = selectedFiles.map(
				(file) => croppedFilesByKey[fileFingerprint(file)] || file
			);
			const isBatch = !isSingleUpload;
			const batchRows = [];
			if (isBatch) {
				clearBatchItemSnapshots(50);
			}

			for (let index = 0; index < filesToProcess.length; index += 1) {
				const originalFile = selectedFiles[index];
				const fileForOcr = filesToProcess[index];
				const originalKey = fileFingerprint(originalFile);
				const progressBase = Math.round((index / filesToProcess.length) * 100);
				setUploadProgress(progressBase);
				setUploadDetail(`Traitement ${index + 1}/${filesToProcess.length} : ${fileForOcr.name}`);

				try {
					const dataUrl = await readFileAsDataUrl(fileForOcr);
					const source = {
						name: fileForOcr.name,
						type: fileForOcr.type,
						size: fileForOcr.size,
						lastModified: fileForOcr.lastModified,
						isCropped: Boolean(croppedFilesByKey[originalKey]),
						dataUrl,
					};

					if (uploadDocumentType === 'invoice') {
						const result = await createInvoiceFromUpload(fileForOcr);
						await fetchInvoiceById(result.id);
						const documentId = result?.numero_facture || `FACT-${result?.id ?? index + 1}`;
						const fields = mapInvoiceBackendToFields(result);
						const rawForStorage = { ...result };

						if (!isBatch && index === 0) {
							clearPreviousInvoiceDraft();
							clearPreviousOcrDraft();
							const invoicePreviewPayload = {
								...source,
								invoiceId: result?.id ?? null,
							};
							writeSessionDocumentPreview('invoice', result?.id, invoicePreviewPayload);
							persistJsonSafely('invoice_uploaded_document', invoicePreviewPayload);
							persistJsonSafely('invoice_latest_result', {
								invoiceId: result?.id ?? null,
								documentId,
								fields,
								rawResult: rawForStorage,
								selectedType: 'invoice',
								savedAt: new Date().toISOString(),
							});
							setLastExtractionType('invoice');
						}

						const batchSnapshot = {
							type: 'invoice',
							result: {
								invoiceId: result?.id ?? null,
								documentId,
								fields,
								rawResult: rawForStorage,
								selectedType: 'invoice',
								savedAt: new Date().toISOString(),
							},
							preview: source,
						};
						if (isBatch) {
							persistBatchItemSnapshot(index, batchSnapshot);
						}

						batchRows.push({
							id: `invoice-${result?.id ?? index}`,
							batchIndex: index,
							fileName: fileForOcr.name,
							type: 'Facture',
							status: 'Succes',
							detailPath: result?.id != null ? `/invoices/${result.id}` : '/invoice-ocr-result',
							documentId,
						});
					} else {
						const result = await extractOcrDocument(fileForOcr);
						const documentId = buildDocumentId(result);
						const fields = mapBackendResultToFields(result);

						if (result?.id != null && result?.storage_local !== true) {
							setErrorMessage(
								'Extraction réussie, mais le fichier DUM n\'a pas été enregistré sur le serveur. ' +
									'L\'aperçu depuis l\'historique ne s\'affichera pas : réimportez ce document après redémarrage de back_EMP (port 8000).'
							);
						}

						if (!isBatch && index === 0) {
							clearPreviousOcrDraft();
							clearPreviousInvoiceDraft();
							persistDocumentPreview({
								...source,
								documentId: result?.id ?? null,
							});
							const latestResult = {
								documentId,
								backendId: result?.id ?? null,
								fields,
								rawResult: buildStoredRawResult(result),
								selectedType: 'declaration',
								savedAt: new Date().toISOString(),
								source: { ...source, documentId: result?.id ?? null },
							};
							persistJsonSafely('ocr_latest_result', latestResult);
							setLastExtractionType('declaration');
						}

						const batchSnapshot = {
							type: 'declaration',
							result: {
								documentId,
								backendId: result?.id ?? null,
								fields,
								rawResult: buildStoredRawResult(result),
								selectedType: 'declaration',
								savedAt: new Date().toISOString(),
							},
							preview: source,
						};
						if (isBatch) {
							persistBatchItemSnapshot(index, batchSnapshot);
						}

						batchRows.push({
							id: `dum-${result?.id ?? index}`,
							batchIndex: index,
							fileName: fileForOcr.name,
							type: 'DUM',
							status: 'Succes',
							detailPath: result?.id != null ? `/documents/${result.id}` : '/ocr-result',
							documentId,
						});
					}
				} catch (fileError) {
					batchRows.push({
						id: `error-${index}`,
						batchIndex: index,
						fileName: fileForOcr.name,
						type: uploadDocumentType === 'invoice' ? 'Facture' : 'DUM',
						status: 'Erreur',
						error: getUploadErrorMessage(fileError, uploadDocumentType === 'invoice'),
					});
				}
			}

			setUploadProgress(100);
			setUploadStatus('completed');

			// 1 seul document : redirection auto vers la page Resultats (DUM ou facture)
			if (isSingleUpload && batchRows[0]?.status === 'Erreur') {
				setUploadStatus('error');
				setErrorMessage(batchRows[0].error || "L'extraction a echoue.");
				return;
			}

			if (isSingleUpload && batchRows[0]?.status === 'Succes') {
				const successRow = batchRows[0];
				const isInvoiceRow = successRow.type === 'Facture';
				let resultsPath = isInvoiceRow ? '/invoice-ocr-result' : '/ocr-result';
				const idFromPath = Number(String(successRow.detailPath || '').split('/').pop());
				if (Number.isFinite(idFromPath) && idFromPath > 0) {
					resultsPath = isInvoiceRow
						? `/invoice-ocr-result?invoiceId=${idFromPath}`
						: `/ocr-result?documentId=${idFromPath}`;
				}
				setUploadDetail(
					isInvoiceRow
						? 'Extraction terminee. Ouverture de Resultats facture…'
						: 'Extraction terminee. Ouverture de Resultats DUM…'
				);
				window.setTimeout(() => {
					const returnKind = consumeCrossVerifyImportReturn();
					const cvSession = getCrossVerificationSession();
					if (isInvoiceRow) {
						if (returnKind === 'invoice' && cvSession?.sourceType && Number.isFinite(idFromPath)) {
							updateCrossVerificationSession({
								pendingPartnerId: idFromPath,
								partnerType: 'invoice',
							});
							navigate('/cross-verification', { replace: true });
							return;
						}
						navigate(resultsPath, { replace: true });
						return;
					}
					if (returnKind === 'dum' && cvSession?.sourceType && Number.isFinite(idFromPath)) {
						updateCrossVerificationSession({ pendingPartnerId: idFromPath, partnerType: 'dum' });
						navigate('/cross-verification', { replace: true });
						return;
					}
					navigate(resultsPath, { replace: true });
				}, 400);
				return;
			}

			setUploadDetail(`Lot termine: ${batchRows.filter((r) => r.status === 'Succes').length}/${batchRows.length} succes`);
			persistJsonSafely('ocr_batch_results', {
				selectedType: uploadDocumentType,
				createdAt: new Date().toISOString(),
				rows: batchRows,
			});
			navigate('/batch-results', { replace: true });
		} catch (error) {
			setUploadStatus('error');
			setUploadProgress(0);
			setUploadDetail('');
			setErrorMessage(getUploadErrorMessage(error, uploadDocumentType === 'invoice'));
		}
	};

	const isUploading = uploadStatus === 'uploading';
	const statusLabelMap = {
		idle: 'En attente de document',
		ready: 'Pret a envoyer',
		uploading: 'Envoi en cours',
		completed: 'Document traite',
		error: 'Erreur de traitement',
	};

	const isInvoiceType = selectedType === 'invoice';
	const isSingleFile = selectedFiles.length === 1;
	const resultsLabel = isInvoiceType ? 'Resultats facture' : 'Resultats DUM';
	const statusDetailMap = {
		idle: 'Ajoutez un fichier pour demarrer le flux OCR.',
		ready: isSingleFile
			? `1 document pret — apres extraction, redirection automatique vers ${resultsLabel}.`
			: `${selectedFiles.length} documents — apres extraction, page Resultats de lot.`,
		uploading: isSingleFile
			? isInvoiceType
				? 'Extraction en cours — redirection automatique vers Resultats facture.'
				: 'Extraction en cours — redirection automatique vers Resultats DUM.'
			: 'Extraction du lot en cours — puis page Resultats de lot.',
		completed: isSingleFile
			? `Document traite. Ouverture de ${resultsLabel}…`
			: 'Lot traite. Ouverture de la page Resultats de lot.',
		error: 'Une erreur est survenue pendant l\'extraction.',
	};

	const workflowSteps = [
		{ label: 'Choix du type de document', state: selectedType ? 'done' : 'pending' },
		{ label: 'Ajout du fichier source', state: selectedFiles.length ? 'done' : 'pending' },
		{
			label: 'Transmission vers OCR',
			state:
				uploadStatus === 'uploading'
					? 'active'
					: uploadStatus === 'completed'
						? 'done'
						: 'pending',
		},
		{ label: 'Extraction et verification', state: uploadStatus === 'completed' ? 'done' : 'pending' },
	];

	const visualProgress =
		uploadStatus === 'ready'
			? 18
			: uploadStatus === 'idle'
				? 0
				: uploadStatus === 'completed'
					? 100
					: uploadProgress;

	return (
		<div className="import-page-container modern-import">
			<section className="dashboard-hero modern import-hero-modern fade-up">
				<div>
					<p className="hero-pill">Flux OCR</p>
					<h1>Import de documents</h1>
					<p className="subtitle">
						Deposez vos fichiers, lancez l&apos;analyse OCR et suivez l&apos;avancement en direct dans une interface
						claire.
					</p>
				</div>
				<div className="import-hero-badges">
					<span className="import-hero-chip">
						<FileBadge2 size={14} /> PDF, JPG, PNG
					</span>
					<span className="import-hero-chip">
						<ShieldCheck size={14} /> Donnees securisees
					</span>
				</div>
			</section>

			{returnToCrossVerify ? (
				<p className="import-return-banner fade-up">
					Extraction pour la <strong>réconciliation DUM vs Facture</strong> — après traitement, vous
					reviendrez à la sélection du document partenaire.
					<Link to="/cross-verification"> Annuler et retour réconciliation</Link>
				</p>
			) : null}

			<div className="import-modern-layout fade-up">
				<section className="import-panel import-modern-panel">
					<div className="import-panel-head">
						<p className="import-panel-kicker">Etape 1</p>
						<h2>Preparation du document</h2>
					</div>

					<FileTypeSelector
						options={fileTypeOptions}
						value={selectedType}
						onChange={setSelectedType}
					/>
					<p className={`import-type-hint ${selectedType}`}>
						{selectedType === 'invoice' ? (
							<>
								<strong>Facture commerciale</strong> — apres extraction, vous serez redirige vers{' '}
								<strong>Resultats facture</strong>.
							</>
						) : (
							<>
								<strong>Declaration DUM</strong> — apres extraction, vous serez redirige vers{' '}
								<strong>Resultats DUM</strong>.
							</>
						)}
					</p>
					<DropZone onFileDrop={handleFileDrop} disabled={isUploading} multiple />
					{selectedFiles.length > 0 ? (
						<p className="import-type-hint">
							{selectedFiles.length === 1 ? (
								<>
									1 fichier pret — apres extraction, redirection automatique vers{' '}
									<strong>{isInvoiceType ? 'Resultats facture' : 'Resultats DUM'}</strong>.
									{selectedFiles[0]?.type?.startsWith('image/')
										? ' Cliquez sur le fichier pour le cadrage personnalise.'
										: null}
								</>
							) : (
								<>
									{selectedFiles.length} fichiers prets — apres extraction, page{' '}
									<strong>Resultats de lot</strong>.
									{selectedFiles.some((f) => f.type?.startsWith('image/'))
										? ' Cliquez sur chaque image pour le cadrage.'
										: null}
								</>
							)}
						</p>
					) : null}
					<FilePreview
						files={selectedFiles}
						onRemove={handleRemoveFile}
						onRemoveAt={handleRemoveFileAt}
						onSelectFile={handleSelectFileForCrop}
						activeFileKey={activeCropKey}
						croppedFileKeys={croppedFileKeys}
						getFileKey={fileFingerprint}
					/>
					{croppedFileKeys.length > 0 ? (
						<p className="import-crop-success">
							<CheckCircle2 size={14} />
							{croppedFileKeys.length} image{croppedFileKeys.length > 1 ? 's' : ''} avec cadrage
							applique — envoi OCR avec rognage pour ces fichiers.
						</p>
					) : null}
					{activeCropKey && activeCropImageUrl && activeCropFile ? (
						<ImageCropper
							key={activeCropKey}
							imageUrl={activeCropImageUrl}
							sourceFile={activeCropFile}
							fileLabel={activeCropFile.name}
							disabled={isUploading}
							onCropApplied={handleCropApplied}
						/>
					) : null}
					<UploadProgress progress={uploadProgress} status={uploadStatus} detail={uploadDetail} />

					<button
						type="button"
						className="auth-button import-submit"
						onClick={startUpload}
						disabled={!selectedFiles.length || isUploading}
					>
						<Upload size={18} />
						{isUploading
							? 'Extraction en cours…'
							: selectedFiles.length > 1
								? `Lancer l'extraction (${selectedFiles.length} fichiers)`
								: "Lancer l'extraction"}
					</button>

					{errorMessage && (
						<p className="profile-message is-error" style={{ marginTop: '0.8rem' }}>
							<AlertTriangle size={16} style={{ marginRight: '0.4rem', verticalAlign: 'text-bottom' }} />
							{errorMessage}
						</p>
					)}

					<p className="import-note">
						Connecte en tant qu&apos;utilisateur authentifie.{' '}
						<Link to="/login" className="auth-link">
							Changer de compte
						</Link>
					</p>
				</section>

				<aside className="import-modern-side">
					<section className="import-side-card">
						<p className="import-side-kicker">Suivi instantane</p>
						<h3>Etat du traitement</h3>
						<p className={`import-side-status ${uploadStatus}`}>{statusLabelMap[uploadStatus]}</p>
						<p className="import-side-detail">{statusDetailMap[uploadStatus]}</p>
						<div className="import-side-meter">
							<span style={{ width: `${visualProgress}%` }} />
						</div>
						<p className="import-side-percent">{Math.round(visualProgress)}%</p>
					</section>

					<section className="import-side-card">
						<p className="import-side-kicker">Workflow</p>
						<h3>Pipeline d&apos;import</h3>
						<div className="import-steps">
							{workflowSteps.map((step) => (
								<div key={step.label} className={`import-step ${step.state}`}>
									<span className="import-step-dot" aria-hidden="true" />
									<span>{step.label}</span>
									{step.state === 'done' ? <CheckCircle2 size={15} /> : null}
								</div>
							))}
						</div>
					</section>

					<section className="import-side-card import-side-tip">
						<Sparkles size={16} />
						<p>
							Pour une extraction plus fiable, privilegiez des scans lisibles avec contraste eleve.
						</p>
					</section>
				</aside>
			</div>
		</div>
	);
}

export default ImportPage;
