function DetailSummaryHeader({ fileLabel, numero, date, metaLine, icon: Icon, iconClassName = '' }) {
	return (
		<div className="detail-summary-title">
			{Icon ? (
				<div className={`detail-doc-icon ${iconClassName}`.trim()}>
					<Icon size={22} />
				</div>
			) : null}
			<div className="detail-summary-title-copy">
				{fileLabel ? <p className="stat-label">{fileLabel}</p> : null}
				<h2 className="detail-summary-numero">
					<span>{numero || '—'}</span>
					{date ? <span className="detail-doc-date-inline"> · {date}</span> : null}
				</h2>
				{metaLine ? <p className="detail-summary-note">{metaLine}</p> : null}
			</div>
		</div>
	);
}

export default DetailSummaryHeader;
