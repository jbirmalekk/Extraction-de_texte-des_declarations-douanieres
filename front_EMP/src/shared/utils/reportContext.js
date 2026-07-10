import { fetchInvoiceById } from '@/shared/services/invoiceApi';
import { fetchDocumentDetail } from '@/shared/services/ocrService';
import { buildComparisonRows, getMontantAlignmentSummary } from '@/shared/utils/compareDisplay';
import {
	buildDumDisplayLine,
	buildInvoiceDisplayLine,
	buildReconciliationPairRef,
	buildReportDocEntries,
} from '@/shared/utils/crossVerifyDisplay';

const parseConfidenceMap = (raw) => {
	if (!raw || typeof raw !== 'object') {
		return null;
	}
	const values = Object.values(raw).filter((v) => typeof v === 'number' && Number.isFinite(v));
	if (!values.length) {
		return null;
	}
	return Math.round(values.reduce((a, b) => a + b, 0) / values.length);
};

export const countComparisonIssues = (rows) =>
	(rows || []).filter((r) => r.tone === 'error' || r.tone === 'warning').length;

export const buildDossierRef = (invoice, dum) =>
	buildReconciliationPairRef(dum, invoice, invoice);

/**
 * Charge le contexte complet d'un rapport (facture + DUM liée).
 * @param {number} invoiceId
 */
export const loadReportContext = async (invoiceId) => {
	const id = Number(invoiceId);
	if (!Number.isFinite(id) || id <= 0) {
		throw new Error('Identifiant facture invalide.');
	}

	const invoice = await fetchInvoiceById(id);
	let dum = null;
	if (invoice?.dum_document_id) {
		dum = await fetchDocumentDetail(invoice.dum_document_id).catch(() => null);
	}

	const comparisonRows = buildComparisonRows(invoice, dum, invoice);
	const amountSummary = getMontantAlignmentSummary(invoice, dum, invoice);
	const issueCount = countComparisonIssues(comparisonRows);
	let fieldConf = invoice?.field_confidence;
	if (typeof fieldConf === 'string') {
		try {
			fieldConf = JSON.parse(fieldConf);
		} catch {
			fieldConf = null;
		}
	}
	const confidence =
		parseConfidenceMap(fieldConf) ??
		(dum?.score_confiance != null ? Number(dum.score_confiance) : null);

	return {
		invoice,
		dum,
		dumId: invoice?.dum_document_id ?? dum?.id ?? null,
		invoiceId: invoice.id,
		comparisonRows,
		amountSummary,
		issueCount,
		confidence,
		dossierRef: buildDossierRef(invoice, dum),
		dumDisplayLine: buildDumDisplayLine(dum, invoice, invoice?.dum_document_id),
		invoiceDisplayLine: buildInvoiceDisplayLine(invoice, invoice, invoice?.id),
		isAligned: amountSummary.aligned,
		statutControle: invoice?.statut_controle || null,
		comparedAt: invoice?.compared_at || null,
		attachments: buildReportDocEntries(dum, invoice),
	};
};
