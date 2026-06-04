/** Cache d'aperçu par document (sessionStorage) — survit à la navigation Import → Historique → Validation. */

const sessionKey = (kind, id) => `emp_${kind}_preview_${Number(id)}`;

const hasPreview = (doc) => Boolean(doc?.dataUrl && typeof doc.dataUrl === 'string');

/** blob: URLs expirent au changement de page — ne jamais les persister ni les relire. */
export const isEphemeralBlobUrl = (url) => typeof url === 'string' && url.startsWith('blob:');

export const isPersistablePreviewDataUrl = (url) =>
	typeof url === 'string' && (url.startsWith('data:') || url.startsWith('http'));

export const isUsableCachedPreview = (preview) =>
	hasPreview(preview) && !isEphemeralBlobUrl(preview.dataUrl);

export const readSessionDocumentPreview = (kind, entityId) => {
	const id = Number(entityId);
	if (!Number.isFinite(id) || id <= 0) {
		return null;
	}
	try {
		const raw = sessionStorage.getItem(sessionKey(kind, id));
		if (!raw) {
			return null;
		}
		const parsed = JSON.parse(raw);
		if (isEphemeralBlobUrl(parsed?.dataUrl)) {
			sessionStorage.removeItem(sessionKey(kind, id));
			return null;
		}
		return isUsableCachedPreview(parsed) ? parsed : null;
	} catch {
		return null;
	}
};

export const removeSessionDocumentPreview = (kind, entityId) => {
	const id = Number(entityId);
	if (!Number.isFinite(id) || id <= 0) {
		return;
	}
	try {
		sessionStorage.removeItem(sessionKey(kind, id));
	} catch {
		/* ignore */
	}
};

export const writeSessionDocumentPreview = (kind, entityId, preview) => {
	if (!isUsableCachedPreview(preview)) {
		return false;
	}
	const id = Number(entityId);
	if (!Number.isFinite(id) || id <= 0) {
		return false;
	}
	try {
		sessionStorage.setItem(
			sessionKey(kind, id),
			JSON.stringify({
				name: preview.name || 'document',
				type: preview.type || 'application/pdf',
				dataUrl: preview.dataUrl,
			})
		);
		return true;
	} catch {
		return false;
	}
};
