import './ui.css';

function formatAmount(val, devise) {
	if (val == null || val === '') {
		return '—';
	}
	const n = Number(val);
	const shown = Number.isFinite(n) ? n.toLocaleString('fr-FR') : String(val);
	return devise ? `${shown} ${devise}` : shown;
}

function DossierSummaryStrip({
	pfn,
	netPay,
	ecart,
	devise = '',
	partnerLabel,
	comparedAt,
	compact = false,
}) {
	const hasAmounts = pfn != null || netPay != null || ecart != null;
	if (!hasAmounts && !partnerLabel) {
		return null;
	}

	const ecartNum = ecart != null ? Number(ecart) : null;
	const ecartClass =
		ecartNum != null && Math.abs(ecartNum) > 0.01 ? 'is-error' : ecartNum != null ? '' : '';

	return (
		<div className={`emp-dossier-summary${compact ? ' emp-dossier-summary--inline' : ''}`}>
			{hasAmounts ? (
				<>
					<div className="emp-dossier-metric">
						<span className="emp-dossier-metric-label">PFN DUM</span>
						<span className="emp-dossier-metric-value">{formatAmount(pfn, devise)}</span>
					</div>
					<div className="emp-dossier-metric">
						<span className="emp-dossier-metric-label">NET PAY</span>
						<span className="emp-dossier-metric-value">{formatAmount(netPay, devise)}</span>
					</div>
					<div className="emp-dossier-metric">
						<span className="emp-dossier-metric-label">Écart</span>
						<span className={`emp-dossier-metric-value ${ecartClass}`.trim()}>
							{formatAmount(ecart, devise)}
						</span>
					</div>
				</>
			) : null}
			{comparedAt ? (
				<div className="emp-dossier-metric">
					<span className="emp-dossier-metric-label">Comparé</span>
					<span className="emp-dossier-metric-value">{comparedAt}</span>
				</div>
			) : null}
			{partnerLabel ? (
				<p className="emp-dossier-partner">
					Lien : <strong>{partnerLabel}</strong>
				</p>
			) : null}
		</div>
	);
}

export default DossierSummaryStrip;
