/** Étapes parcours EMP : Import → OCR → Validation → Réconciliation → ERP */
export const WORKFLOW_STEPS = [
	{ key: 'import', label: 'Import', short: 'Imp.' },
	{ key: 'ocr', label: 'OCR', short: 'OCR' },
	{ key: 'validation', label: 'Validation', short: 'Val.' },
	{ key: 'cross', label: 'Réconciliation', short: 'Réco.' },
	{ key: 'erp', label: 'ERP', short: 'ERP' },
];

const withStates = (states) =>
	WORKFLOW_STEPS.map((step, i) => ({
		...step,
		state: states[i] || 'pending',
	}));

/** Progression depuis une ligne historique unifiée. */
export const getWorkflowProgressFromHistoryRow = (row) => {
	if (!row) {
		return withStates(['pending', 'pending', 'pending', 'pending', 'pending']);
	}

	const validated =
		row.statusFilterKey === 'validated' ||
		row.status === 'Validé' ||
		row.status === 'Contrôlé';
	const inProgress =
		row.statusFilterKey === 'in_progress' || row.statusFilterKey === 'pending';
	const reconciled = Boolean(row.isReconciled);
	const reconOk = row.controleStatut === 'ok';

	if (!validated && inProgress) {
		return withStates(['done', 'done', 'current', 'pending', 'pending']);
	}
	if (!validated) {
		return withStates(['done', 'current', 'pending', 'pending', 'pending']);
	}
	if (validated && !reconciled) {
		return withStates(['done', 'done', 'done', 'current', 'pending']);
	}
	if (reconciled && !reconOk) {
		return withStates(['done', 'done', 'done', 'current', 'pending']);
	}
	if (reconOk) {
		return withStates(['done', 'done', 'done', 'done', 'current']);
	}
	return withStates(['done', 'done', 'done', 'current', 'pending']);
};

/** Progression page validation (document en cours de correction). */
export const getWorkflowProgressForValidation = ({
	validated = false,
	reconciled = false,
	reconOk = false,
	erpReady = false,
} = {}) => {
	if (erpReady) {
		return withStates(['done', 'done', 'done', 'done', 'done']);
	}
	if (reconOk) {
		return withStates(['done', 'done', 'done', 'done', 'current']);
	}
	if (reconciled) {
		return withStates(['done', 'done', 'done', 'current', 'pending']);
	}
	if (validated) {
		return withStates(['done', 'done', 'done', 'current', 'pending']);
	}
	return withStates(['done', 'done', 'current', 'pending', 'pending']);
};

/** Stats rapides pour la page rapports. */
export const computeReportsStats = (items = []) => {
	let ok = 0;
	let warn = 0;
	let err = 0;
	for (const inv of items) {
		if (inv.statut_controle === 'ok') ok += 1;
		else if (inv.statut_controle === 'warning') warn += 1;
		else if (inv.statut_controle === 'error') err += 1;
	}
	return { total: items.length, ok, warn, err };
};
