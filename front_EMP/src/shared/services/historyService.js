import { bulkDeleteInvoices } from '@/shared/services/invoiceApi';
import { bulkDeleteDocuments } from '@/shared/services/ocrService';
import { removeSessionDocumentPreview } from '@/shared/utils/documentPreviewCache';
import { fetchUnifiedHistoryApi } from '@/shared/services/unifiedHistoryApi';
import { splitUnifiedHistoryResponse } from '@/shared/utils/historyUnified';

export const HISTORY_BATCH_SIZE = 30;
export const HISTORY_MAX_RECORDS = 500;

/**
 * Historique DUM paginé (back_EMP).
 * @param {{ isAdmin?: boolean, skip?: number, limit?: number }} opts
 */
export const fetchDumHistoryPage = async ({ isAdmin = false, skip = 0, limit = HISTORY_BATCH_SIZE } = {}) => {
	const fetcher = isAdmin ? fetchAdminHistory : fetchMyHistory;
	const data = await fetcher({ skip, limit });
	return {
		history: data?.history || [],
		total: data?.total ?? (data?.history?.length ?? 0),
		skip: data?.skip ?? skip,
		limit: data?.limit ?? limit,
		stats: data?.stats || {},
	};
};

/**
 * Page factures paginée (back_EMP_Fact), filtrée par utilisateur si non-admin.
 * @param {{ skip?: number, limit?: number }} params
 * @param {{ id?: number, role?: string } | null} user
 */
export const fetchInvoiceHistoryPage = async (params = {}, user = null) => {
	try {
		return await fetchInvoicesList(
			{ skip: params.skip ?? 0, limit: params.limit ?? HISTORY_BATCH_SIZE },
			user
		);
	} catch {
		return {
			items: [],
			total: 0,
			skip: params.skip ?? 0,
			limit: params.limit ?? HISTORY_BATCH_SIZE,
		};
	}
};

/**
 * Charge un lot DUM + factures via GET /api/history (back_EMP, authentifié).
 */
export const fetchUnifiedHistoryBatch = async ({
	skip = 0,
	limit = HISTORY_BATCH_SIZE,
	type = 'all',
} = {}) => {
	const data = await fetchUnifiedHistoryApi({ skip, limit, type });
	const split = splitUnifiedHistoryResponse(data);
	return {
		...split,
		hasMoreDum: skip + split.dumHistory.length < split.dumTotal,
		hasMoreInvoice: skip + split.invoiceItems.length < split.invoiceTotal,
	};
};

/**
 * Charge tout l'historique par lots (plafond HISTORY_MAX_RECORDS par source).
 */
export const fetchUnifiedHistoryAll = async () => {
	let skip = 0;
	let dumHistory = [];
	let invoiceItems = [];
	let dumTotal = 0;
	let invoiceTotal = 0;
	let ownerCount = 0;
	let invoiceSource = null;

	while (skip < HISTORY_MAX_RECORDS) {
		const page = await fetchUnifiedHistoryBatch({
			skip,
			limit: HISTORY_BATCH_SIZE,
			type: 'all',
		});
		if (!page.dumHistory.length && !page.invoiceItems.length) {
			break;
		}
		dumHistory = [...dumHistory, ...page.dumHistory];
		invoiceItems = [...invoiceItems, ...page.invoiceItems];
		dumTotal = page.dumTotal;
		invoiceTotal = page.invoiceTotal;
		ownerCount = page.ownerCount;
		invoiceSource = page.invoiceSource;
		skip += page.dumHistory.length + page.invoiceItems.length;
		if (skip >= dumTotal + invoiceTotal) {
			break;
		}
	}

	return {
		dumHistory,
		invoiceItems,
		dumTotal,
		invoiceTotal,
		ownerCount,
		hasMoreDum: false,
		hasMoreInvoice: false,
		invoiceSource,
	};
};

/** @deprecated Préférer fetchUnifiedHistoryBatch / fetchUnifiedHistoryAll */
export const fetchUnifiedHistory = async ({ isAdmin = false, user = null } = {}) => {
	return fetchUnifiedHistoryAll({ isAdmin, user });
};

/**
 * Historique via GET /api/history (back_EMP, fusion côté serveur si INVOICE_API_URL).
 * Retourne des lignes brutes ; mapper avec historyUnified si besoin UI.
 */
/**
 * Supprime les lignes sélectionnées (DUM + factures).
 * @param {Array<{ type: 'dum'|'invoice', dumId?: number, invoiceId?: number }>} rows
 * @param {{ id?: number, role?: string } | null} user
 */
export const deleteHistoryRows = async (rows, user = null) => {
	const dumIds = rows.filter((r) => r.type === 'dum').map((r) => r.dumId).filter(Boolean);
	const invoiceIds = rows.filter((r) => r.type === 'invoice').map((r) => r.invoiceId).filter(Boolean);

	const results = { dum: { deleted: [], failed: [] }, invoice: { deleted: [], failed: [] } };

	if (dumIds.length) {
		results.dum = await bulkDeleteDocuments(dumIds);
		for (const id of results.dum.deleted || []) {
			removeSessionDocumentPreview('dum', id);
		}
	}
	if (invoiceIds.length) {
		results.invoice = await bulkDeleteInvoices(invoiceIds);
		for (const id of results.invoice.deleted || []) {
			removeSessionDocumentPreview('invoice', id);
		}
	}

	return results;
};

export const fetchServerUnifiedHistory = async ({
	type = 'all',
	skip = 0,
	limit = HISTORY_BATCH_SIZE,
} = {}) => {
	try {
		return await fetchUnifiedHistoryApi({ type, skip, limit });
	} catch {
		return null;
	}
};
