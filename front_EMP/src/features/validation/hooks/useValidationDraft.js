import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { prepareValidationPayloadForStorage } from '../utils/documentContextStorage';

const fieldsFingerprint = (fields = []) =>
	fields
		.map((f) => `${f.id}|${f.key}|${String(f.value ?? '')}`)
		.join('\n');

/**
 * Brouillon local : indicateur non enregistré + sauvegarde auto périodique.
 */
export function useValidationDraft({
	storageKey,
	fields,
	payload,
	setPayload,
	buildModifiedMap,
	intervalMs = 30000,
	enabled = true,
}) {
	const [lastSavedAt, setLastSavedAt] = useState(payload?.savedAt ?? null);
	const [autoSaving, setAutoSaving] = useState(false);
	const savedFingerprintRef = useRef(
		payload?.fields ? fieldsFingerprint(payload.fields) : fieldsFingerprint(fields)
	);

	useEffect(() => {
		if (payload?.savedAt) {
			setLastSavedAt(payload.savedAt);
		}
		if (payload?.fields?.length) {
			savedFingerprintRef.current = fieldsFingerprint(payload.fields);
		}
	}, [payload?.savedAt]);

	const isDirty = useMemo(() => {
		if (!enabled || !fields.length) {
			return false;
		}
		return fieldsFingerprint(fields) !== savedFingerprintRef.current;
	}, [fields, enabled]);

	const persistDraft = useCallback(
		({ silent = false } = {}) => {
			if (!storageKey || !payload) {
				return false;
			}
			const modifiedFields = buildModifiedMap(fields);
			const savedAt = new Date().toISOString();
			const updatedPayload = prepareValidationPayloadForStorage({
				...payload,
				fields,
				modifiedFields,
				savedAt,
			});
			try {
				localStorage.setItem(storageKey, JSON.stringify(updatedPayload));
			} catch (error) {
				console.warn(`Impossible de sauvegarder ${storageKey}`, error);
				return false;
			}
			setPayload(updatedPayload);
			setLastSavedAt(savedAt);
			savedFingerprintRef.current = fieldsFingerprint(fields);
			if (!silent) {
				setAutoSaving(false);
			}
			return true;
		},
		[storageKey, payload, fields, buildModifiedMap, setPayload]
	);

	const markDraftSaved = useCallback(() => {
		savedFingerprintRef.current = fieldsFingerprint(fields);
	}, [fields]);

	useEffect(() => {
		if (!enabled || !isDirty || !storageKey) {
			return undefined;
		}
		const timer = window.setInterval(() => {
			setAutoSaving(true);
			persistDraft({ silent: true });
			setAutoSaving(false);
		}, intervalMs);
		return () => window.clearInterval(timer);
	}, [enabled, isDirty, storageKey, intervalMs, persistDraft]);

	const lastSavedLabel = lastSavedAt
		? new Date(lastSavedAt).toLocaleString('fr-FR', {
				day: '2-digit',
				month: '2-digit',
				hour: '2-digit',
				minute: '2-digit',
			})
		: null;

	return {
		isDirty,
		lastSavedAt,
		lastSavedLabel,
		autoSaving,
		persistDraft,
		markDraftSaved,
	};
}
