import DocTypeBadge from '@/shared/components/ui/DocTypeBadge';
import StatusBadge from '@/shared/components/ui/StatusBadge';
import './ui.css';

/** Colonne réconciliation : état + partenaire (n° + date DUM ou facture). */
function ReconciliationCell({
	statusLabel = '—',
	statusTone = 'neutral',
	partnerType,
	partnerNumero,
	partnerDate,
}) {
	const hasPartner = Boolean(partnerNumero || partnerDate);

	if (!hasPartner && statusLabel === '—') {
		return <span className="emp-recon-cell emp-recon-cell--empty">—</span>;
	}

	return (
		<div className="emp-recon-cell">
			<StatusBadge label={statusLabel} tone={statusTone} />
			{hasPartner ? (
				<div className="emp-recon-partner">
					{partnerType ? <DocTypeBadge type={partnerType} /> : null}
					<div className="emp-recon-partner-lines">
						{partnerNumero ? <strong>{partnerNumero}</strong> : null}
						{partnerDate ? <span>{partnerDate}</span> : null}
					</div>
				</div>
			) : null}
		</div>
	);
}

export default ReconciliationCell;
