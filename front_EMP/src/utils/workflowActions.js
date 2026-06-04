/** DUM validée en base (statut OCR). */
export const isDumValidated = (statutOrLabel) => {
	const s = String(statutOrLabel || '').toLowerCase();
	return s === 'validated' || s === 'valide' || statutOrLabel === 'Validé';
};

/** Facture validée ou déjà passée au contrôle croisé. */
export const isInvoiceValidated = (statut) => {
	const s = String(statut || '').toLowerCase();
	return s === 'valide' || s === 'controle_croise';
};

/** Ligne historique : masquer le bouton Validation. */
export const isHistoryRowValidated = (row) => {
	if (!row) {
		return false;
	}
	if (row.type === 'dum') {
		return row.statusFilterKey === 'validated' || isDumValidated(row.status);
	}
	return row.statusFilterKey === 'validated';
};

export const isReconciliationControlOk = (statutControle) => statutControle === 'ok';

/** Rapport conforme : pas de correction DUM/facture. */
export const isReportConforme = ({ statutControle, amountAligned, issueCount = 0 }) =>
	isReconciliationControlOk(statutControle) && Boolean(amountAligned) && issueCount === 0;

/** ID facture pour « Voir le rapport » (réconciliation OK). */
export const historyReportInvoiceId = (row) => {
	if (!row || !isReconciliationControlOk(row.controleStatut) || !row.isReconciled) {
		return null;
	}
	return row.type === 'invoice' ? row.invoiceId : row.linkedInvoiceId;
};

export const showHistoryValidationButton = (row) => !isHistoryRowValidated(row);

export const showHistoryReconcileButton = (row) =>
	!isReconciliationControlOk(row?.controleStatut);

export const showHistoryReportLink = (row) => historyReportInvoiceId(row) != null;

/** Cible export ERP depuis une ligne historique (dossier prioritaire). */
export const getHistoryErpExportTarget = (row) => {
	if (!row) {
		return null;
	}
	const dossierInvoiceId = historyReportInvoiceId(row);
	if (dossierInvoiceId) {
		return {
			kind: 'dossier',
			invoiceId: dossierInvoiceId,
			dumId: row.type === 'dum' ? row.dumId : row.linkedDumId ?? row.dumId,
			reference: row.reference,
			statutControle: row.controleStatut,
			isAmountAligned: row.controleStatut === 'ok',
		};
	}
	if (row.type === 'dum' && isHistoryRowValidated(row) && row.dumId) {
		return {
			kind: 'dum',
			documentId: row.dumId,
			dumId: row.dumId,
			reference: row.reference,
		};
	}
	if (row.type === 'invoice' && isHistoryRowValidated(row) && row.invoiceId) {
		return {
			kind: 'invoice',
			invoiceId: row.invoiceId,
			documentId: row.invoiceId,
			reference: row.reference,
		};
	}
	return null;
};

export const showHistoryErpExportButton = (row) => getHistoryErpExportTarget(row) != null;
