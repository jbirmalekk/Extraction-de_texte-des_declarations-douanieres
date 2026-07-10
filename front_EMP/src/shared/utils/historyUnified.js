const parseDate = (value) => {
	if (!value) {
		return null;
	}
	const d = new Date(value);
	return Number.isNaN(d.getTime()) ? null : d;
};

export const formatHistoryDateTime = (isoOrDate) => {
	const d = parseDate(isoOrDate);
	if (!d) {
		return '—';
	}
	return d.toLocaleString('fr-FR', {
		day: '2-digit',
		month: '2-digit',
		year: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
	});
};

const invoiceStatusMap = {
	extracted: { label: 'Extrait', tone: 'warning', filterKey: 'in_progress' },
	valide: { label: 'Validé', tone: 'success', filterKey: 'validated' },
	controle_croise: { label: 'Contrôlé', tone: 'success', filterKey: 'validated' },
};

const trimOrNull = (value) => {
	const s = String(value ?? '').trim();
	return s || null;
};

import { isDumValidated, isInvoiceValidated } from '@/shared/utils/workflowActions';

const dumStatusFilterKey = (statusLabel) => {
	if (statusLabel === 'Validé') {
		return 'validated';
	}
	if (statusLabel === 'Rejeté') {
		return 'rejected';
	}
	if (statusLabel === 'En cours') {
		return 'in_progress';
	}
	return 'pending';
};

export const reconciliationStatusFromControle = (statutControle) => {
	if (statutControle === 'ok') {
		return { label: 'Conforme', tone: 'ok' };
	}
	if (statutControle === 'warning') {
		return { label: 'Attention', tone: 'warning' };
	}
	if (statutControle === 'error') {
		return { label: 'Écart', tone: 'error' };
	}
	if (statutControle) {
		return { label: 'Comparé', tone: 'warning' };
	}
	return { label: '—', tone: 'neutral' };
};

const reconciliationFromInvoice = (inv) => {
	if (!inv?.dum_document_id) {
		return { label: '—', tone: 'neutral' };
	}
	const sc = inv.statut_controle;
	if (sc === 'ok') {
		return { label: `DUM #${inv.dum_document_id} · OK`, tone: 'ok' };
	}
	if (sc === 'warning') {
		return { label: `DUM #${inv.dum_document_id} · Attention`, tone: 'warning' };
	}
	if (sc === 'error') {
		return { label: `DUM #${inv.dum_document_id} · Écart`, tone: 'error' };
	}
	if (inv.compared_at) {
		return { label: `DUM #${inv.dum_document_id} · Comparé`, tone: 'warning' };
	}
	return { label: `DUM #${inv.dum_document_id}`, tone: 'neutral' };
};

/** @param {Map<number, object>} invoiceByDumId */
export const mapDumHistoryRow = (row, invoiceByDumId) => {
	const linked = invoiceByDumId.get(row.document_id);
	let reconciliation = { label: '—', tone: 'neutral' };
	let reconciliationStatus = reconciliationStatusFromControle(null);
	let reconciliationPartner = {
		partnerType: null,
		partnerNumero: null,
		partnerDate: null,
	};

	let linkedPartnerValidated = null;
	if (linked) {
		reconciliationStatus = reconciliationStatusFromControle(linked.statut_controle);
		reconciliation = {
			label: `Facture ${linked.numero_facture || `#${linked.id}`}`,
			tone: reconciliationStatus.tone,
		};
		linkedPartnerValidated = isInvoiceValidated(linked.statut);
		reconciliationPartner = {
			partnerType: 'invoice',
			partnerNumero:
				trimOrNull(linked.numero_facture) || `FACT-${linked.id}`,
			partnerDate: trimOrNull(linked.date_facture),
		};
	}

	const createdIso = row.created_at || row.validated_at || `${row.date}T00:00:00`;
	const correctionsCount = row.corrections_count ?? 0;
	const correctionsHint =
		correctionsCount > 0
			? `${correctionsCount} correction${correctionsCount > 1 ? 's' : ''}${
					row.validator ? ` · ${row.validator}` : ''
				}`
			: null;

	return {
		id: `dum-${row.document_id}`,
		type: 'dum',
		typeLabel: 'DUM',
		reference: row.numero_declaration || row.document || `DUM #${row.document_id}`,
		declarationDate: row.date_declaration || null,
		fileName: row.fichier || row.document || '',
		owner: row.owner || null,
		dateIso: createdIso,
		dateLabel: formatHistoryDateTime(createdIso),
		status: row.status || 'En attente',
		statusTone: row.tone || 'warning',
		statusFilterKey: dumStatusFilterKey(row.status),
		sourceValidated: dumStatusFilterKey(row.status) === 'validated' || isDumValidated(row.status),
		linkedPartnerValidated: linkedPartnerValidated,
		reconciliationLabel: reconciliation.label,
		reconciliationTone: reconciliation.tone,
		reconciliationStatusLabel: reconciliationStatus.label,
		reconciliationStatusTone: reconciliationStatus.tone,
		reconciliationPartnerType: reconciliationPartner.partnerType,
		reconciliationPartnerNumero: reconciliationPartner.partnerNumero,
		reconciliationPartnerDate: reconciliationPartner.partnerDate,
		correctionsCount,
		correctionsHint,
		score: row.score ?? null,
		dumId: row.document_id,
		invoiceId: linked?.id ?? null,
		linkedInvoiceId: linked?.id ?? null,
		linkedDumId: null,
		isReconciled: Boolean(linked?.compared_at || linked?.statut_controle),
		controleStatut: linked?.statut_controle ?? null,
		pfnDum: linked?.montant_declare_dum ?? null,
		netPay: linked?.net_pay ?? null,
		ecartMontant: linked?.ecart_montant ?? null,
		deviseControle: linked?.devise_declaree_dum || linked?.devise || null,
		comparedAtLabel: formatHistoryDateTime(linked?.compared_at),
	};
};

/** Ligne facture renvoyée par GET /api/history (type invoice). */
export const mapUnifiedInvoiceToListItem = (row) => ({
	id: row.document_id,
	fichier_nom: row.fichier || '',
	numero_facture: row.numero_facture,
	date_facture: row.date_facture || null,
	owner: row.owner || null,
	statut: row.status || row.statut || 'extracted',
	statut_controle: row.statut_controle,
	dum_document_id: row.dum_document_id,
	numero_declaration_dum: row.numero_declaration_dum ?? null,
	date_declaration_dum: row.date_declaration_dum ?? null,
	net_pay: row.net_pay,
	devise: row.devise,
	compared_at: row.compared_at,
	created_at: row.created_at,
});

export const splitUnifiedHistoryResponse = (data) => {
	const items = data?.items || [];
	const dumHistory = items
		.filter((item) => item.type === 'dum')
		.map(({ type: _t, ...row }) => row);
	const invoiceItems = items
		.filter((item) => item.type === 'invoice')
		.map(mapUnifiedInvoiceToListItem);
	const ownerSet = new Set(
		[...dumHistory, ...invoiceItems].map((r) => r.owner).filter(Boolean)
	);
	return {
		dumHistory,
		invoiceItems,
		dumTotal: data?.dum_total ?? dumHistory.length,
		invoiceTotal: data?.invoice_total ?? invoiceItems.length,
		ownerCount: ownerSet.size,
		invoiceSource: data?.invoice_source,
	};
};

/** @param {Map<number, object>} [dumById] lignes DUM historique (document_id → row) */
export const mapInvoiceHistoryRow = (inv, dumById) => {
	const st = invoiceStatusMap[inv.statut] || {
		label: inv.statut || 'Extrait',
		tone: 'warning',
		filterKey: 'in_progress',
	};
	const rec = reconciliationFromInvoice(inv);
	const createdIso = inv.created_at || null;
	const reconciliationStatus = inv.dum_document_id
		? reconciliationStatusFromControle(inv.statut_controle)
		: reconciliationStatusFromControle(null);

	const dumId = inv.dum_document_id != null ? Number(inv.dum_document_id) : null;
	const linkedDum = dumId != null && dumById ? dumById.get(dumId) : null;
	const reconciliationPartner = dumId
		? {
				partnerType: 'dum',
				partnerNumero:
					trimOrNull(inv.numero_declaration_dum) ||
					trimOrNull(linkedDum?.numero_declaration) ||
					`DUM #${dumId}`,
				partnerDate:
					trimOrNull(inv.date_declaration_dum) ||
					trimOrNull(linkedDum?.date_declaration) ||
					null,
			}
		: {
				partnerType: null,
				partnerNumero: null,
				partnerDate: null,
			};

	const linkedPartnerValidated = dumId
		? isDumValidated(linkedDum?.status) || linkedDum?.status === 'Validé'
		: null;

	return {
		id: `invoice-${inv.id}`,
		type: 'invoice',
		typeLabel: 'Facture',
		reference: inv.numero_facture || `FACT-${inv.id}`,
		invoiceDate: inv.date_facture || null,
		fileName: inv.fichier_nom || '',
		owner: inv.owner || null,
		dateIso: createdIso,
		dateLabel: formatHistoryDateTime(createdIso),
		status: st.label,
		statusTone: st.tone,
		statusFilterKey: inv.compared_at ? 'reconciled' : st.filterKey,
		sourceValidated: isInvoiceValidated(inv.statut),
		linkedPartnerValidated,
		reconciliationLabel: rec.label,
		reconciliationTone: rec.tone,
		reconciliationStatusLabel: reconciliationStatus.label,
		reconciliationStatusTone: reconciliationStatus.tone,
		reconciliationPartnerType: reconciliationPartner.partnerType,
		reconciliationPartnerNumero: reconciliationPartner.partnerNumero,
		reconciliationPartnerDate: reconciliationPartner.partnerDate,
		correctionsCount: '—',
		correctionsHint: null,
		score: inv.net_pay != null ? `${inv.net_pay} ${inv.devise || ''}`.trim() : null,
		dumId: inv.dum_document_id ?? null,
		invoiceId: inv.id,
		linkedInvoiceId: null,
		linkedDumId: inv.dum_document_id ?? null,
		isReconciled: Boolean(inv.compared_at || inv.statut_controle),
		controleStatut: inv.statut_controle ?? null,
		pfnDum: inv.montant_declare_dum ?? null,
		netPay: inv.net_pay ?? null,
		ecartMontant: inv.ecart_montant ?? null,
		deviseControle: inv.devise_declaree_dum || inv.devise || null,
		comparedAtLabel: formatHistoryDateTime(inv.compared_at),
	};
};

export const buildInvoiceByDumMap = (invoices) => {
	const map = new Map();
	for (const inv of invoices || []) {
		if (inv.dum_document_id != null) {
			map.set(Number(inv.dum_document_id), inv);
		}
	}
	return map;
};

export const buildDumByIdMap = (dumHistory) => {
	const map = new Map();
	for (const row of dumHistory || []) {
		const id = row.document_id ?? row.id;
		if (id != null) {
			map.set(Number(id), row);
		}
	}
	return map;
};

export const mergeHistoryRows = (dumHistory, invoices) => {
	const invoiceByDum = buildInvoiceByDumMap(invoices);
	const dumById = buildDumByIdMap(dumHistory);
	const dumRows = (dumHistory || []).map((row) => mapDumHistoryRow(row, invoiceByDum));
	const invoiceRows = (invoices || []).map((inv) => mapInvoiceHistoryRow(inv, dumById));
	return [...dumRows, ...invoiceRows].sort((a, b) => {
		const ta = parseDate(a.dateIso)?.getTime() ?? 0;
		const tb = parseDate(b.dateIso)?.getTime() ?? 0;
		return tb - ta;
	});
};

const matchesSearch = (row, query) => {
	if (!query) {
		return true;
	}
	const q = query.toLowerCase();
	return [row.reference, row.fileName, row.owner, row.reconciliationLabel, row.typeLabel]
		.filter(Boolean)
		.some((s) => String(s).toLowerCase().includes(q));
};

export const filterHistoryRows = (rows, { search = '', type = 'all', status = 'all', periodDays = 0 } = {}) => {
	const now = Date.now();
	const periodMs = periodDays > 0 ? periodDays * 24 * 60 * 60 * 1000 : 0;

	return rows.filter((row) => {
		if (type !== 'all' && row.type !== type) {
			return false;
		}
		if (status === 'validated' && row.statusFilterKey !== 'validated') {
			return false;
		}
		if (status === 'in_progress' && row.statusFilterKey !== 'in_progress' && row.statusFilterKey !== 'pending') {
			return false;
		}
		if (status === 'rejected' && row.statusFilterKey !== 'rejected') {
			return false;
		}
		if (status === 'reconciled' && !row.isReconciled) {
			return false;
		}
		if (periodMs > 0) {
			const t = parseDate(row.dateIso)?.getTime();
			if (!t || now - t > periodMs) {
				return false;
			}
		}
		return matchesSearch(row, search);
	});
};

export const computeHistoryStats = (rows, { isAdmin = false, ownerCount = 0 } = {}) => {
	const total = rows.length;
	const validated = rows.filter((r) => r.statusFilterKey === 'validated').length;
	const inProgress = rows.filter(
		(r) => r.statusFilterKey === 'in_progress' || r.statusFilterKey === 'pending'
	).length;
	const reconciledOk = rows.filter((r) => r.reconciliationTone === 'ok').length;
	const reconciledWarn = rows.filter(
		(r) => r.isReconciled && (r.reconciliationTone === 'warning' || r.reconciliationTone === 'error')
	).length;

	return {
		total,
		validated,
		inProgress,
		reconciledOk,
		reconciledWarn,
		owners: isAdmin ? ownerCount : null,
	};
};

export const exportHistoryToCsv = (rows) => {
	const headers = [
		'Type',
		'Référence',
		'Fichier',
		'Propriétaire',
		'Date',
		'Statut',
		'Réconciliation',
		'Statut contrôle',
		'PFN DUM',
		'NET PAY',
		'Écart montant',
		'Devise contrôle',
		'Date comparaison',
		'ID DUM',
		'ID Facture',
		'Corrections',
	];
	const lines = rows.map((r) =>
		[
			r.typeLabel,
			r.reference,
			r.fileName,
			r.owner || '',
			r.dateLabel,
			r.status,
			r.reconciliationLabel,
			r.controleStatut || '—',
			r.pfnDum != null ? r.pfnDum : '—',
			r.netPay != null ? r.netPay : '—',
			r.ecartMontant != null ? r.ecartMontant : '—',
			r.deviseControle || '—',
			r.comparedAtLabel || '—',
			r.dumId ?? '—',
			r.invoiceId ?? '—',
			r.correctionsCount,
		]
			.map((c) => `"${String(c).replace(/"/g, '""')}"`)
			.join(';')
	);
	return [headers.join(';'), ...lines].join('\n');
};
