import axios from 'axios';
import apiClient, { API_BASE_URL } from './api';

/**
 * Factures via proxy back_EMP (/api/invoices) — même session JWT (cookies).
 * Définir VITE_INVOICE_API_BASE_URL=http://localhost:8001 seulement pour debug direct.
 */
const DIRECT_INVOICE_BASE = (import.meta.env.VITE_INVOICE_API_BASE_URL || '').trim();
const USE_DIRECT = Boolean(DIRECT_INVOICE_BASE) && DIRECT_INVOICE_BASE !== API_BASE_URL;

export const invoiceApiClient = USE_DIRECT
	? axios.create({
			baseURL: DIRECT_INVOICE_BASE,
			withCredentials: true,
			timeout: 600_000,
			headers: { 'Content-Type': 'application/json' },
		})
	: apiClient;

const buildClientPcName = () => {
	if (typeof window === 'undefined') {
		return 'unknown-client';
	}
	const host = window.location.hostname || '';
	const platform = window.navigator?.platform || '';
	return [host && host !== 'localhost' ? host : 'browser-client', platform].filter(Boolean).join(' | ').slice(0, 255);
};

/**
 * Crée une facture : upload fichier + extraction + persistance (back_EMP_Fact via proxy).
 */
export const createInvoiceFromUpload = async (file, { onUploadProgress, clientPcName } = {}) => {
	const formData = new FormData();
	formData.append('file', file);
	const headers = {
		'Content-Type': 'multipart/form-data',
		'X-Client-PC-Name': clientPcName || buildClientPcName(),
	};
	const { data } = await invoiceApiClient.post('/api/invoices', formData, {
		headers,
		onUploadProgress,
		timeout: 600_000,
	});
	return data;
};

export const patchInvoice = async (invoiceId, payload) => {
	const { data } = await invoiceApiClient.patch(`/api/invoices/${invoiceId}`, payload);
	return data;
};

/** @deprecated Les en-têtes X-User-* ne sont plus utilisés (JWT / proxy). */
export const buildInvoiceAuthHeaders = () => ({});

export const normalizeInvoiceListPage = (data) => {
	if (Array.isArray(data)) {
		return {
			items: data,
			total: data.length,
			skip: 0,
			limit: data.length,
		};
	}
	return {
		items: data?.items ?? [],
		total: data?.total ?? 0,
		skip: data?.skip ?? 0,
		limit: data?.limit ?? 50,
	};
};

export const INVOICE_LIST_TIMEOUT_MS = 20_000;

export const fetchInvoicesList = async (params = {}, _user = null, { timeoutMs } = {}) => {
	const { data } = await invoiceApiClient.get('/api/invoices', {
		params,
		timeout: timeoutMs ?? INVOICE_LIST_TIMEOUT_MS,
	});
	return normalizeInvoiceListPage(data);
};

export const fetchInvoiceById = async (invoiceId) => {
	const { data } = await invoiceApiClient.get(`/api/invoices/${invoiceId}`);
	return data;
};

export const bulkDeleteInvoices = async (ids) => {
	const { data } = await invoiceApiClient.post('/api/invoices/bulk-delete', { ids });
	return data;
};

export const fetchInvoiceByDumId = async (dumDocumentId) => {
	const { data } = await invoiceApiClient.get(`/api/invoices/by-dum/${dumDocumentId}`);
	return data;
};

export const linkInvoiceToDum = async (invoiceId, body) => {
	const { data } = await invoiceApiClient.post(`/api/invoices/${invoiceId}/link-dum`, body);
	return data;
};

export const compareInvoiceWithDum = async (invoiceId, body) => {
	const { data } = await invoiceApiClient.post(
		`/api/invoices/${invoiceId}/compare-dum`,
		body,
		{ timeout: 600_000 }
	);
	return data;
};
