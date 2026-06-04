import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { formatMoney } from './compareDisplay';

const formatDateFr = (iso) => {
	if (!iso) {
		return '—';
	}
	const d = new Date(iso);
	return Number.isNaN(d.getTime()) ? String(iso) : d.toLocaleString('fr-FR');
};

const fileSlug = (comparison, invoiceId) => {
	const ref =
		comparison?.numero_declaration_dum ||
		comparison?.numero_facture ||
		invoiceId ||
		'rapport';
	return String(ref).replace(/[^\w.-]+/g, '_').slice(0, 48);
};

/**
 * Export PDF stylisé du rapport de vérification croisée.
 */
export const exportComparisonReportPdf = ({
	comparison,
	dumDetail = null,
	invoiceDetail = null,
	comparisonRows = [],
	amountSummary = null,
	dossierRef = '',
	confidence = null,
	issueCount = 0,
}) => {
	const doc = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' });
	const pageW = doc.internal.pageSize.getWidth();
	const dev = amountSummary?.devise || comparison?.devise || '';
	const aligned = amountSummary?.aligned ?? false;
	const statut = comparison?.statut_controle || '—';
	const invId = invoiceDetail?.id ?? comparison?.id;
	const dumId = dumDetail?.id ?? comparison?.dum_document_id;

	// En-tête
	doc.setFillColor(37, 99, 235);
	doc.rect(0, 0, pageW, 32, 'F');
	doc.setTextColor(255, 255, 255);
	doc.setFont('helvetica', 'bold');
	doc.setFontSize(15);
	doc.text('EMP SmartOCR', 14, 12);
	doc.setFont('helvetica', 'normal');
	doc.setFontSize(10);
	doc.text('Rapport de vérification croisée DUM — Facture fournisseur', 14, 20);

	let y = 40;

	// Bandeau alerte
	if (!aligned || statut === 'error') {
		doc.setFillColor(254, 226, 226);
		doc.setDrawColor(248, 113, 113);
		doc.roundedRect(14, y, pageW - 28, 22, 2, 2, 'FD');
		doc.setTextColor(153, 27, 27);
		doc.setFont('helvetica', 'bold');
		doc.setFontSize(11);
		doc.text('Alerte : écart détecté sur les montants ou le contrôle', 18, y + 8);
		doc.setFont('helvetica', 'normal');
		doc.setFontSize(9);
		doc.text(dossierRef || `Facture #${invId} · DUM #${dumId ?? '—'}`, 18, y + 15);
		y += 28;
	} else if (statut === 'warning') {
		doc.setFillColor(255, 251, 235);
		doc.setDrawColor(251, 191, 36);
		doc.roundedRect(14, y, pageW - 28, 20, 2, 2, 'FD');
		doc.setTextColor(180, 83, 9);
		doc.setFont('helvetica', 'bold');
		doc.setFontSize(10);
		doc.text('Attention : points à vérifier (montants OK)', 18, y + 8);
		doc.setFont('helvetica', 'normal');
		doc.setFontSize(9);
		doc.text(dossierRef || '', 18, y + 14);
		y += 26;
	} else {
		doc.setFillColor(240, 253, 244);
		doc.setDrawColor(134, 239, 172);
		doc.roundedRect(14, y, pageW - 28, 18, 2, 2, 'FD');
		doc.setTextColor(22, 101, 52);
		doc.setFont('helvetica', 'bold');
		doc.setFontSize(10);
		doc.text('Contrôle conforme — PFN et NET PAY alignés', 18, y + 11);
		y += 24;
	}

	// KPI
	doc.setTextColor(30, 41, 59);
	doc.setFont('helvetica', 'normal');
	doc.setFontSize(9);
	const kpiW = (pageW - 28 - 8) / 3;
	const kpiLabels = ['Confiance OCR', 'Nombre d\'écarts', 'Date comparaison'];
	const kpiValues = [
		confidence != null ? `${confidence} %` : '—',
		String(issueCount),
		formatDateFr(comparison?.compared_at),
	];
	for (let i = 0; i < 3; i += 1) {
		const x = 14 + i * (kpiW + 4);
		doc.setFillColor(248, 250, 252);
		doc.setDrawColor(226, 232, 240);
		doc.roundedRect(x, y, kpiW, 20, 2, 2, 'FD');
		doc.setFont('helvetica', 'normal');
		doc.setFontSize(8);
		doc.setTextColor(100, 116, 139);
		doc.text(kpiLabels[i], x + 4, y + 7);
		doc.setFont('helvetica', 'bold');
		doc.setFontSize(12);
		doc.setTextColor(15, 23, 42);
		doc.text(kpiValues[i], x + 4, y + 15);
	}
	y += 28;

	// Résumé montants
	doc.setFont('helvetica', 'bold');
	doc.setFontSize(10);
	doc.setTextColor(15, 23, 42);
	doc.text('Synthèse financière', 14, y);
	y += 6;
	doc.setFont('helvetica', 'normal');
	doc.setFontSize(9);
	const summaryLines = [
		`PFN DUM : ${amountSummary?.pfn != null ? formatMoney(amountSummary.pfn, dev) : '—'}`,
		`NET PAY facture : ${amountSummary?.netPay != null ? formatMoney(amountSummary.netPay, dev) : '—'}`,
		`Écart : ${amountSummary?.ecartAbs != null ? formatMoney(amountSummary.ecartAbs, dev) : '—'}`,
		`Statut : ${statut} · ${comparison?.ecart_commentaire || ''}`.trim(),
	];
	summaryLines.forEach((line) => {
		doc.text(line, 14, y);
		y += 5;
	});
	y += 4;

	// Tableau
	autoTable(doc, {
		startY: y,
		head: [['Champ de données', 'Valeur DUM', 'Valeur facture', 'Écart', 'Statut']],
		body: (comparisonRows || []).map((r) => [
			r.categorie,
			r.dumValue,
			r.factureValue,
			r.ecart,
			r.statut,
		]),
		styles: {
			fontSize: 8,
			cellPadding: 2.5,
			lineColor: [226, 232, 240],
			lineWidth: 0.1,
		},
		headStyles: {
			fillColor: [37, 99, 235],
			textColor: 255,
			fontStyle: 'bold',
		},
		columnStyles: {
			0: { cellWidth: 48 },
			4: { cellWidth: 22, halign: 'center' },
		},
		didParseCell: (data) => {
			if (data.section !== 'body') {
				return;
			}
			const row = comparisonRows[data.row.index];
			if (!row) {
				return;
			}
			if (row.tone === 'error') {
				data.cell.styles.fillColor = [254, 226, 226];
				data.cell.styles.textColor = [153, 27, 27];
			} else if (row.tone === 'warning') {
				data.cell.styles.fillColor = [255, 251, 235];
				data.cell.styles.textColor = [180, 83, 9];
			} else if (row.tone === 'ok') {
				data.cell.styles.fillColor = [240, 253, 244];
			}
		},
		margin: { left: 14, right: 14 },
	});

	const finalY = doc.lastAutoTable?.finalY ?? y + 40;
	let footY = finalY + 10;

	if (footY > 260) {
		doc.addPage();
		footY = 20;
	}

	doc.setFont('helvetica', 'normal');
	doc.setFontSize(8);
	doc.setTextColor(100, 116, 139);
	doc.text(`Généré le ${formatDateFr(new Date().toISOString())} — EMP SmartOCR PFE`, 14, footY);
	footY += 5;
	if (dumDetail?.fichier || invoiceDetail?.fichier_nom) {
		doc.text(
			`Pièces : ${[dumDetail?.fichier, invoiceDetail?.fichier_nom].filter(Boolean).join(' · ')}`,
			14,
			footY
		);
	}

	doc.save(`rapport_verification_${fileSlug(comparison, invId)}.pdf`);
};
