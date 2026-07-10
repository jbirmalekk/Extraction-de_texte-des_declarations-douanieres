import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchDumSourcePreview, fetchInvoiceSourcePreview } from '../services/documentPreviewApi';
import { resolveStoredDocumentPreview } from '../utils/compareDocumentPreview';
import {
	isEphemeralBlobUrl,
	isUsableCachedPreview,
	removeSessionDocumentPreview,
} from '../utils/documentPreviewCache';
import { cacheDocumentPreview } from '../utils/documentContextStorage';

const hasDataUrl = (doc) => Boolean(doc?.dataUrl && typeof doc.dataUrl === 'string');

const revokeBlobUrl = (preview) => {
	if (preview?.isBlobUrl && preview?.dataUrl?.startsWith('blob:')) {
		URL.revokeObjectURL(preview.dataUrl);
	}
};

/** Cache mémoire (data: URLs seulement — les blob: expirent). */
const previewCache = new Map();
const previewFailed = new Map();
const previewInflight = new Map();

const cacheKey = (kind, id) => `${kind}:${id}`;

const FILE_MISSING_MSG = {
	dum: 'Fichier DUM introuvable sur le serveur. Réimportez ce document depuis Import (type DUM).',
	invoice:
		'Fichier facture introuvable sur le serveur. Réimportez depuis Import (type Facture).',
};

const usablePreview = (candidate) => {
	if (!hasDataUrl(candidate)) {
		return null;
	}
	if (isEphemeralBlobUrl(candidate.dataUrl) && candidate.isBlobUrl) {
		return candidate;
	}
	if (isEphemeralBlobUrl(candidate.dataUrl)) {
		return null;
	}
	return candidate;
};

/**
 * Aperçu document : sessionStorage (data: seulement) puis fichier GED via API.
 */
export function useDocumentFilePreview({
	kind,
	entityId,
	payloadSource = null,
	fileName = '',
	contentType = '',
	sourceFileAvailable = null,
}) {
	const [preview, setPreview] = useState(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState('');
	const [reloadNonce, setReloadNonce] = useState(0);
	const activeBlobRef = useRef(null);

	const sourceDataUrl = payloadSource?.dataUrl ?? '';
	const sourceName = payloadSource?.name ?? '';
	const sourceType = payloadSource?.type ?? '';

	const reload = useCallback(() => {
		const id = Number(entityId);
		if (Number.isFinite(id) && id > 0) {
			invalidateDocumentPreviewCache(kind, id);
		}
		setReloadNonce((n) => n + 1);
	}, [kind, entityId]);

	useEffect(() => {
		let cancelled = false;

		const load = async () => {
			const id = Number(entityId);
			if (!Number.isFinite(id) || id <= 0) {
				setPreview(usablePreview(payloadSource));
				setLoading(false);
				setError('');
				return;
			}

			const key = cacheKey(kind, id);

			const stored = usablePreview(resolveStoredDocumentPreview(kind, id));
			if (stored) {
				setPreview(stored);
				setLoading(false);
				setError('');
				return;
			}

			const fromPayload = usablePreview(payloadSource);
			if (fromPayload && !fromPayload.isBlobUrl) {
				setPreview(fromPayload);
				setLoading(false);
				setError('');
				return;
			}

			if (sourceFileAvailable === false) {
				const msg = previewFailed.get(key) || FILE_MISSING_MSG[kind];
				setPreview(null);
				setLoading(false);
				setError(msg);
				return;
			}

			const memCached = previewCache.get(key);
			if (memCached && isUsableCachedPreview(memCached)) {
				setPreview(memCached);
				setLoading(false);
				setError('');
				return;
			}

			if (previewFailed.has(key)) {
				setPreview(null);
				setLoading(false);
				setError(previewFailed.get(key));
				return;
			}

			if (previewInflight.has(key)) {
				setLoading(true);
				try {
					const remote = await previewInflight.get(key);
					if (!cancelled) {
						setPreview(remote);
						setError('');
					}
				} catch (err) {
					if (!cancelled) {
						setPreview(null);
						setError(previewFailed.get(key) || err?.message || FILE_MISSING_MSG[kind]);
					}
				} finally {
					if (!cancelled) {
						setLoading(false);
					}
				}
				return;
			}

			setLoading(true);
			setError('');
			setPreview(null);

			const fetchPromise = (async () => {
				const remote =
					kind === 'invoice'
						? await fetchInvoiceSourcePreview(id, { name: fileName, type: contentType })
						: await fetchDumSourcePreview(id, { name: fileName, type: contentType });
				if (isUsableCachedPreview(remote)) {
					previewCache.set(key, remote);
				}
				return remote;
			})();

			previewInflight.set(key, fetchPromise);

			try {
				const remote = await fetchPromise;
				if (cancelled) {
					revokeBlobUrl(remote);
					return;
				}
				if (activeBlobRef.current) {
					revokeBlobUrl(activeBlobRef.current);
				}
				if (remote?.isBlobUrl) {
					activeBlobRef.current = remote;
				} else {
					activeBlobRef.current = null;
					cacheDocumentPreview(kind, id, remote);
				}
				setPreview(remote);
				setError('');
			} catch (err) {
				if (!cancelled) {
					const status = err?.response?.status;
					const detail = err?.response?.data?.detail;
					const detailText = typeof detail === 'string' ? detail : detail?.message || '';
					let msg = detailText || err?.message || FILE_MISSING_MSG[kind];
					if (status === 403) {
						msg =
							detailText ||
							'Accès refusé à ce document. Ouvrez-le depuis votre historique ou réimportez-le.';
					} else if (status === 404) {
						msg = detailText || FILE_MISSING_MSG[kind];
					}
					previewFailed.set(key, msg);
					setPreview(null);
					setError(msg);
				}
			} finally {
				previewInflight.delete(key);
				if (!cancelled) {
					setLoading(false);
				}
			}
		};

		load();

		return () => {
			cancelled = true;
		};
	}, [kind, entityId, sourceDataUrl, sourceName, sourceType, sourceFileAvailable, reloadNonce]);

	useEffect(
		() => () => {
			if (activeBlobRef.current) {
				revokeBlobUrl(activeBlobRef.current);
				activeBlobRef.current = null;
			}
		},
		[]
	);

	return { preview, loading, error, reload };
}

/** Invalide le cache après réimport, blob expiré ou suppression. */
export const invalidateDocumentPreviewCache = (kind, entityId) => {
	const id = Number(entityId);
	if (!Number.isFinite(id) || id <= 0) {
		return;
	}
	const key = cacheKey(kind, id);
	const cached = previewCache.get(key);
	if (cached) {
		revokeBlobUrl(cached);
	}
	previewCache.delete(key);
	previewFailed.delete(key);
	previewInflight.delete(key);
	removeSessionDocumentPreview(kind, id);
};
