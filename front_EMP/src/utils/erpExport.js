/** Types d'export ERP (simulation → /erp-success, future API Uniges). */
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
			return 'DUM envoyée vers l’ERP';
		case ERP_EXPORT.INVOICE:
			return 'Facture envoyée vers l’ERP';
		case ERP_EXPORT.DOSSIER:
			return 'Dossier exporté vers l’ERP';
		default:
			return 'Export ERP enregistré';
	}
};

export const getErpSuccessMessage = (kind, reference) => {
	const ref = reference ? ` (${reference})` : '';
	switch (kind) {
		case ERP_EXPORT.DUM:
			return `La déclaration DUM validée${ref} est prête pour l’intégration ERP (Uniges).`;
		case ERP_EXPORT.INVOICE:
			return `La facture validée${ref} est prête pour l’intégration ERP (Uniges).`;
		case ERP_EXPORT.DOSSIER:
			return `Le dossier de contrôle (DUM + facture + réconciliation)${ref} est prêt pour l’ERP.`;
		default:
			return 'Export simulé — branchement API Uniges à venir.';
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

/**
 * Export dossier (réconciliation / rapport) — mêmes garde-fous que la conformité.
 * @returns {boolean} true si navigation effectuée
 */
export const requestDossierErpExport = ({
	navigate,
	statutControle,
	isAmountAligned,
	isAdmin = false,
	invoiceId,
	dumId,
	reference,
	onError,
}) => {
	if (!isAmountAligned) {
		onError?.(
			'Export ERP refusé : les montants PFN DUM et NET PAY doivent être alignés.'
		);
		return false;
	}

	if (statutControle === 'error' && !isAdmin) {
		onError?.(
			'Export ERP impossible : écarts critiques. Corrigez les documents ou demandez un override administrateur.'
		);
		return false;
	}

	if (statutControle === 'error' && isAdmin) {
		const confirmed = window.confirm(
			'Écarts critiques détectés. Confirmez-vous l’export ERP malgré les écarts ?'
		);
		if (!confirmed) {
			return false;
		}
	}

	if (statutControle === 'warning') {
		const confirmed = window.confirm(
			'Des points d’attention subsistent (poids, incoterm, etc.). Confirmez-vous l’export ERP ?'
		);
		if (!confirmed) {
			return false;
		}
	}

	navigateToErpSuccess(navigate, {
		kind: ERP_EXPORT.DOSSIER,
		invoiceId: invoiceId ?? null,
		dumId: dumId ?? null,
		reference: reference ?? null,
		statutControle: statutControle ?? null,
	});
	return true;
};
