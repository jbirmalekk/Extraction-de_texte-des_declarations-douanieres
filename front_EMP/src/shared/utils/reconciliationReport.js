import { buildComparisonRows, formatMoney, getMontantAlignmentSummary } from '@/shared/utils/compareDisplay';

const csvEscape = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;

const formatIso = (iso) => {
	if (!iso) {
		return '—';
	}
	const d = new Date(iso);
	return Number.isNaN(d.getTime()) ? String(iso) : d.toLocaleString('fr-FR');
};

/**
 * Export CSV d'un contrôle DUM ↔ facture (résumé + lignes du tableau).
 */
export const exportComparisonReportCsv = ({
	comparison,
	dumDetail = null,
	invoiceDetail = null,
	dumId,
	invoiceId,
	sourceLabel = '',
}) => {
	const rows = buildComparisonRows(comparison, dumDetail, invoiceDetail);
	const summary = getMontantAlignmentSummary(comparison, dumDetail, invoiceDetail);
	const dev = summary.devise || '';

	const metaLines = [
		['Rapport de vérification croisée DUM — Facture'],
		['Généré le', formatIso(new Date().toISOString())],
		['Source', sourceLabel || '—'],
		['ID DUM', dumId ?? dumDetail?.id ?? '—'],
		['ID Facture', invoiceId ?? invoiceDetail?.id ?? '—'],
		['N° déclaration DUM', comparison?.numero_declaration_dum || dumDetail?.numero_declaration || '—'],
		['N° facture', comparison?.numero_facture || invoiceDetail?.numero_facture || '—'],
		['PFN DUM', summary.pfn != null ? formatMoney(summary.pfn, dev) : '—'],
		['NET PAY facture', summary.netPay != null ? formatMoney(summary.netPay, dev) : '—'],
		[
			'Écart montant (abs.)',
			summary.ecartAbs != null ? formatMoney(summary.ecartAbs, dev) : '—',
		],
		['Montants alignés', summary.aligned ? 'Oui' : 'Non'],
		['Statut contrôle', comparison?.statut_controle || '—'],
		['Commentaire', comparison?.ecart_commentaire || '—'],
		['Date comparaison', formatIso(comparison?.compared_at)],
		[],
		['Catégorie', 'Valeur DUM', 'Valeur facture', 'Écart', 'Statut ligne'],
	];

	const tableLines = rows.map((r) => [
		r.categorie,
		r.dumValue,
		r.factureValue,
		r.ecart,
		r.statut,
	]);

	const csv = [...metaLines, ...tableLines]
		.map((line) => line.map(csvEscape).join(';'))
		.join('\n');

	const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	const ref = comparison?.numero_declaration_dum || dumId || 'controle';
	a.href = url;
	a.download = `rapport_verification_${ref}_${new Date().toISOString().slice(0, 10)}.csv`;
	a.click();
	URL.revokeObjectURL(url);
};

/** Ligne historique / rapport — export CSV liste. */
export const exportReconciliationListCsv = (rows, { filenamePrefix = 'rapports_controles' } = {}) => {
	const headers = [
		'Type',
		'Référence',
		'Fichier',
		'Date',
		'Statut document',
		'Réconciliation',
		'Statut contrôle',
		'PFN DUM',
		'NET PAY',
		'Écart montant',
		'Devise contrôle',
		'Date comparaison',
		'ID DUM',
		'ID Facture',
	];
	const lines = rows.map((r) => [
		r.typeLabel,
		r.reference,
		r.fileName,
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
	]);
	const csv = [headers.join(';'), ...lines.map((line) => line.map(csvEscape).join(';'))].join('\n');
	const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = `${filenamePrefix}_${new Date().toISOString().slice(0, 10)}.csv`;
	a.click();
	URL.revokeObjectURL(url);
};
