import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createInvoiceFromUpload, fetchInvoiceById } from '@/shared/services/invoiceApi';
import { extractOcrDocument } from '@/shared/services/ocrService';
import { mapInvoiceBackendToFields } from '@/shared/utils/invoiceFields';
import { DEFAULT_DOCUMENT_ID, mapBackendResultToFields } from '@/shared/utils/ocrFields';
import { setLastExtractionType } from '@/shared/utils/extractionRouting';
import {
	consumeCrossVerifyImportReturn,
	getCrossVerificationSession,
	updateCrossVerificationSession,
} from '@/shared/utils/crossVerificationSession';
import { writeSessionDocumentPreview } from '@/shared/utils/documentPreviewCache';

const ExtractionJobsContext = createContext(null);

const IDLE_STATE = {
	status: 'idle', // idle | running | error
	docType: 'declaration',
	isBatch: false,
	total: 0,
	progress: 0,
	detail: '',
	error: '',
	jobs: [],
};

const RAW_RESULT_STORAGE_EXCLUDE = new Set(['texte_brut', 'texte_nettoye']);

const readFileAsDataUrl = (file) =>
	new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(reader.result);
		reader.onerror = () => reject(new Error('Impossible de lire le document.'));
		reader.readAsDataURL(file);
	});

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

const buildLightPreview = (source) => {
	if (!source || typeof source !== 'object') {
		return source;
	}
	const { dataUrl: _dataUrl, ...meta } = source;
	return meta;
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

export function ExtractionJobsProvider({ children }) {
	const navigate = useNavigate();
	const [state, setState] = useState(IDLE_STATE);
	const runningRef = useRef(false);

	const reset = useCallback(() => {
		runningRef.current = false;
		setState(IDLE_STATE);
	}, []);

	const startExtraction = useCallback(
		async ({ files, croppedFilesByKey = {}, uploadDocumentType, returnToCrossVerify = false }) => {
			if (runningRef.current || !files?.length) {
				return;
			}
			runningRef.current = true;

			const isSingleUpload = files.length === 1;
			const isBatch = !isSingleUpload;
			const isInvoice = uploadDocumentType === 'invoice';

			const filesToProcess = files.map(
				(file) => croppedFilesByKey[fileFingerprint(file)] || file
			);

			setState({
				status: 'running',
				docType: uploadDocumentType,
				isBatch,
				total: filesToProcess.length,
				progress: 0,
				detail: `Préparation de ${filesToProcess.length} document(s)…`,
				error: '',
				jobs: filesToProcess.map((f) => ({ fileName: f.name, status: 'pending' })),
			});

			const setJobStatus = (index, status, extra = {}) => {
				setState((prev) => {
					const jobs = prev.jobs.slice();
					if (jobs[index]) {
						jobs[index] = { ...jobs[index], status, ...extra };
					}
					return { ...prev, jobs };
				});
			};

			const batchRows = [];
			if (isBatch) {
				clearBatchItemSnapshots(50);
			}

			try {
				for (let index = 0; index < filesToProcess.length; index += 1) {
					const originalFile = files[index];
					const fileForOcr = filesToProcess[index];
					const originalKey = fileFingerprint(originalFile);
					const progressBase = Math.round((index / filesToProcess.length) * 100);

					setState((prev) => ({
						...prev,
						progress: progressBase,
						detail: `Traitement ${index + 1}/${filesToProcess.length} : ${fileForOcr.name}`,
					}));
					setJobStatus(index, 'processing');

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

						if (isInvoice) {
							const result = await createInvoiceFromUpload(fileForOcr);
							await fetchInvoiceById(result.id);
							const documentId = result?.numero_facture || `FACT-${result?.id ?? index + 1}`;
							const fields = mapInvoiceBackendToFields(result);
							const rawForStorage = { ...result };

							if (!isBatch && index === 0) {
								clearPreviousInvoiceDraft();
								clearPreviousOcrDraft();
								const invoicePreviewPayload = { ...source, invoiceId: result?.id ?? null };
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
								preview: buildLightPreview(source),
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
								backendId: result?.id ?? null,
								detailPath: result?.id != null ? `/invoices/${result.id}` : '/invoice-ocr-result',
								documentId,
							});
							setJobStatus(index, 'done', { documentId });
						} else {
							const result = await extractOcrDocument(fileForOcr);
							const documentId = buildDocumentId(result);
							const fields = mapBackendResultToFields(result);

							if (!isBatch && index === 0) {
								clearPreviousOcrDraft();
								clearPreviousInvoiceDraft();
								persistDocumentPreview({ ...source, documentId: result?.id ?? null });
								persistJsonSafely('ocr_latest_result', {
									documentId,
									backendId: result?.id ?? null,
									fields,
									rawResult: buildStoredRawResult(result),
									selectedType: 'declaration',
									savedAt: new Date().toISOString(),
									source: { ...source, documentId: result?.id ?? null },
								});
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
								preview: buildLightPreview(source),
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
								backendId: result?.id ?? null,
								detailPath: result?.id != null ? `/documents/${result.id}` : '/ocr-result',
								documentId,
							});
							setJobStatus(index, 'done', { documentId });
						}
					} catch (fileError) {
						const message = getUploadErrorMessage(fileError, isInvoice);
						batchRows.push({
							id: `error-${index}`,
							batchIndex: index,
							fileName: fileForOcr.name,
							type: isInvoice ? 'Facture' : 'DUM',
							status: 'Erreur',
							error: message,
						});
						setJobStatus(index, 'error', { error: message });
					}
				}

				setState((prev) => ({ ...prev, progress: 100 }));

				// 1 seul document en erreur : rester sur la page Import avec message.
				if (isSingleUpload && batchRows[0]?.status === 'Erreur') {
					runningRef.current = false;
					setState((prev) => ({
						...prev,
						status: 'error',
						error: batchRows[0].error || "L'extraction a echoue.",
					}));
					return;
				}

				// 1 seul document réussi : redirection vers Résultats (DUM/facture ou réconciliation).
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

					const returnKind = consumeCrossVerifyImportReturn();
					const cvSession = getCrossVerificationSession();
					let target = resultsPath;
					if (isInvoiceRow) {
						if (returnKind === 'invoice' && cvSession?.sourceType && Number.isFinite(idFromPath)) {
							updateCrossVerificationSession({ pendingPartnerId: idFromPath, partnerType: 'invoice' });
							target = '/cross-verification';
						}
					} else if (returnKind === 'dum' && cvSession?.sourceType && Number.isFinite(idFromPath)) {
						updateCrossVerificationSession({ pendingPartnerId: idFromPath, partnerType: 'dum' });
						target = '/cross-verification';
					}

					runningRef.current = false;
					setState(IDLE_STATE);
					navigate(target, { replace: true });
					return;
				}

				// Lot : page Résultats de lot (liste des fichiers extraits à vérifier).
				persistJsonSafely('ocr_batch_results', {
					selectedType: uploadDocumentType,
					createdAt: new Date().toISOString(),
					rows: batchRows,
				});
				runningRef.current = false;
				setState(IDLE_STATE);
				navigate('/batch-results', { replace: true });
			} catch (error) {
				runningRef.current = false;
				setState((prev) => ({
					...prev,
					status: 'error',
					progress: 0,
					error: getUploadErrorMessage(error, isInvoice),
				}));
			}
		},
		[navigate]
	);

	const value = useMemo(
		() => ({ ...state, startExtraction, reset }),
		[state, startExtraction, reset]
	);

	return <ExtractionJobsContext.Provider value={value}>{children}</ExtractionJobsContext.Provider>;
}

export function useExtractionJobs() {
	const ctx = useContext(ExtractionJobsContext);
	if (!ctx) {
		throw new Error('useExtractionJobs must be used within ExtractionJobsProvider');
	}
	return ctx;
}
