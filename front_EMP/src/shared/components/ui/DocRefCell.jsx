import './ui.css';

function DocRefCell({ numero, date, fileName, inlineDate = true }) {
	return (
		<span className="emp-doc-ref">
			<span className="emp-doc-ref-line">
				<strong>{numero || '—'}</strong>
				{date && inlineDate ? (
					<span className="emp-doc-ref-date emp-doc-ref-date--inline"> · {date}</span>
				) : null}
			</span>
			{date && !inlineDate ? <span className="emp-doc-ref-date">{date}</span> : null}
			{fileName ? <small>{fileName}</small> : null}
		</span>
	);
}

export default DocRefCell;
