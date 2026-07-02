/** DUM validée en base (statut OCR). */
export const isDumValidated = (statutOrLabel) => {
	const s = String(statutOrLabel || '').toLowerCase();
	return s === 'validated' || s === 'valide' || statutOrLabel === 'Validé';
};

/** Facture validée ou déjà passée au contrôle croisé. */
export const isInvoiceValidated = (statut) => {
	const s = String(statut || '').toLowerCase();
	return (
		s === 'valide' ||
		s === 'controle_croise' ||
		s === 'controle_ok' ||
		s === 'controle_warning' ||
		s === 'controle_ecart'
	);
};

/** Contrôle terminé avec écart ou attention → nouvelle réconciliation possible. */
export const isReconciliationNeedsRedo = (statutControle) =>
	statutControle === 'error' || statutControle === 'warning';

export const RECONCILIATION_BLOCKED_MSG =
	'La vérification croisée nécessite une DUM et une facture validées (étape Validation terminée).';

/** Afficher le bouton Réconciliation (source validée ; partenaire lié non validé = masqué). */
export const canShowReconciliation = ({
	sourceValidated,
	linkedPartnerValidated,
	reconOk,
}) => {
	if (reconOk) {
		return false;
	}
	if (!sourceValidated) {
		return false;
	}
	if (linkedPartnerValidated === false) {
		return false;
	}
	return true;
};

/** Ligne historique : masquer le bouton Validation. */
export const isHistoryRowValidated = (row) => {
	if (!row) {
		return false;
	}
	if (row.type === 'dum') {
		return Boolean(row.sourceValidated);
	}
	return Boolean(row.sourceValidated);
};

export const isReconciliationControlOk = (statutControle) => statutControle === 'ok';

/** Rapport conforme : pas de correction DUM/facture. */
export const isReportConforme = ({ statutControle, amountAligned, issueCount = 0 }) =>
	isReconciliationControlOk(statutControle) && Boolean(amountAligned) && issueCount === 0;

/** ID facture pour « Voir le rapport » (après au moins une comparaison). */
export const historyReportInvoiceId = (row) => {
	if (!row) {
		return null;
	}
	const invoiceId = row.type === 'invoice' ? row.invoiceId : row.linkedInvoiceId;
	if (!invoiceId) {
		return null;
	}
	if (!row.controleStatut && !row.isReconciled) {
		return null;
	}
	return invoiceId;
};

export const showHistoryValidationButton = (row) => !isHistoryRowValidated(row);

export const showHistoryReconcileButton = (row) => {
	if (!row?.sourceValidated) {
		return false;
	}
	if (isReconciliationControlOk(row?.controleStatut)) {
		return false;
	}
	if (isReconciliationNeedsRedo(row?.controleStatut)) {
		return true;
	}
	return canShowReconciliation({
		sourceValidated: true,
		linkedPartnerValidated: row?.linkedPartnerValidated,
		reconOk: false,
	});
};

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

/** Vérifier qu’un couple DUM + facture peut être comparé. */
export const assertReconciliationPairReady = ({ dumStatut, invoiceStatut }) => {
	if (!isDumValidated(dumStatut)) {
		return { ok: false, message: 'La DUM doit être validée avant la vérification croisée.' };
	}
	if (!isInvoiceValidated(invoiceStatut)) {
		return { ok: false, message: 'La facture doit être validée avant la vérification croisée.' };
	}
	return { ok: true, message: '' };
};
