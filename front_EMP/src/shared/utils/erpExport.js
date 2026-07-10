import { postErpMigration, postErpValidationData } from '@/shared/services/erpApi';

export const ERP_EXPORT = {
	DUM: 'dum',
	INVOICE: 'invoice',
	DOSSIER: 'dossier',
};

export const getErpExportLabel = (kind) => {
	switch (kind) {
		case ERP_EXPORT.DUM:
			return 'Envoyer DUM vers ERP';
		case ERP_EXPORT.INVOICE:
			return 'Envoyer facture vers ERP';
		case ERP_EXPORT.DOSSIER:
			return 'Exporter dossier vers ERP';
		default:
			return 'Export ERP';
	}
};

export const getErpSuccessTitle = (kind) => {
	switch (kind) {
		case ERP_EXPORT.DUM:
			return 'DUM intégrée à l’ERP';
		case ERP_EXPORT.INVOICE:
			return 'Facture intégrée à l’ERP';
		case ERP_EXPORT.DOSSIER:
			return 'Dossier intégré à l’ERP';
		default:
			return 'Intégration ERP terminée';
	}
};

export const getErpSuccessMessage = (kind, reference, erpReference) => {
	const ref = reference ? ` (${reference})` : '';
	const erp = erpReference ? ` Référence ERP : ${erpReference}.` : '';
	switch (kind) {
		case ERP_EXPORT.DUM:
			return `La DUM${ref} a été enregistrée sur le serveur OCR puis migrée vers l’ERP.${erp}`;
		case ERP_EXPORT.INVOICE:
			return `La facture${ref} a été enregistrée sur le serveur OCR puis migrée vers l’ERP.${erp}`;
		case ERP_EXPORT.DOSSIER:
			return `Le dossier (DUM + facture + contrôle)${ref} a été migré vers l’ERP.${erp}`;
		default:
			return `Intégration ERP réussie.${erp}`;
	}
};

export const navigateToErpSuccess = (navigate, exportPayload) => {
	navigate('/erp-success', {
		state: {
			erpExport: {
				...exportPayload,
				exportedAt: new Date().toISOString(),
			},
		},
	});
};

const resolveIdsForKind = (kind, { invoiceId, dumId, documentId }) => {
	const inv = invoiceId ?? (kind === ERP_EXPORT.INVOICE ? documentId : null);
	const dum = dumId ?? (kind === ERP_EXPORT.DUM ? documentId : null);
	return {
		invoiceId: inv != null ? Number(inv) : null,
		dumDocumentId: dum != null ? Number(dum) : null,
	};
};

/**
 * Pipeline Front → S1 (JSON en BD) → S2 (migration ERP).
 */
export const executeErpIntegration = async ({
	kind,
	invoiceId = null,
	dumId = null,
	documentId = null,
	reference = null,
}) => {
	const { invoiceId: invId, dumDocumentId } = resolveIdsForKind(kind, {
		invoiceId,
		dumId,
		documentId,
	});

	const stored = await postErpValidationData({
		kind,
		dumDocumentId,
		invoiceId: invId,
		reference,
	});

	const migration = await postErpMigration(stored.export_id);

	return {
		exportId: stored.export_id,
		kind: stored.kind,
		reference: stored.reference ?? reference,
		storedStatus: stored.status,
		migration,
		erpReference: migration.erp_reference ?? null,
	};
};

const formatErpError = (err) => {
	const detail = err?.response?.data?.detail;
	if (typeof detail === 'string') {
		return detail;
	}
	if (Array.isArray(detail)) {
		return detail.map((d) => d.msg || JSON.stringify(d)).join(' · ');
	}
	return err?.message || 'Échec de l’intégration ERP.';
};

/** Bloque ou prépare le message de confirmation avant export ERP. */
export const getErpExportGate = ({
	kind = ERP_EXPORT.DOSSIER,
	statutControle = null,
	isAmountAligned = true,
	isAdmin = false,
}) => {
	if (kind === ERP_EXPORT.DOSSIER) {
		if (!isAmountAligned) {
			return {
				allowed: false,
				reason:
					'Export ERP refusé : les montants PFN DUM et NET PAY doivent être alignés.',
			};
		}

		if (statutControle === 'error' && !isAdmin) {
			return {
				allowed: false,
				reason:
					'Export ERP impossible : écarts critiques. Corrigez les documents ou demandez un override administrateur.',
			};
		}

		if (statutControle === 'error' && isAdmin) {
			return {
				allowed: true,
				confirmMessage:
					'Écarts critiques détectés. Confirmez-vous l’intégration ERP malgré les écarts ?',
			};
		}

		if (statutControle === 'warning') {
			return {
				allowed: true,
				confirmMessage:
					'Des points d’attention subsistent. Confirmez-vous l’intégration ERP ?',
			};
		}
	}

	const action = getErpExportLabel(kind).toLowerCase();
	return {
		allowed: true,
		confirmMessage: `Confirmez-vous ${action} vers l’ERP ? Les données seront enregistrées puis migrées.`,
	};
};

/**
 * Export ERP avec garde-fous métier (dossier) puis pipeline S1 + S2.
 * La confirmation utilisateur est gérée par ErpExportButton (panneau intégré).
 */
export const requestErpExport = async ({
	navigate,
	kind = ERP_EXPORT.DOSSIER,
	statutControle = null,
	isAmountAligned = true,
	isAdmin = false,
	invoiceId = null,
	dumId = null,
	documentId = null,
	reference = null,
	onError,
}) => {
	const gate = getErpExportGate({ kind, statutControle, isAmountAligned, isAdmin });
	if (!gate.allowed) {
		onError?.(gate.reason);
		return false;
	}

	try {
		const result = await executeErpIntegration({
			kind,
			invoiceId,
			dumId,
			documentId,
			reference,
		});

		navigateToErpSuccess(navigate, {
			kind,
			invoiceId: invoiceId ?? (kind === ERP_EXPORT.INVOICE ? documentId : null),
			dumId: dumId ?? (kind === ERP_EXPORT.DUM ? documentId : null),
			reference: result.reference,
			exportId: result.exportId,
			erpReference: result.erpReference,
			statutControle,
			migrationMessage: result.migration?.message,
		});
		return true;
	} catch (err) {
		onError?.(formatErpError(err));
		return false;
	}
};

/** @deprecated Utiliser requestErpExport */
export const requestDossierErpExport = (opts) =>
	requestErpExport({ ...opts, kind: ERP_EXPORT.DOSSIER });
