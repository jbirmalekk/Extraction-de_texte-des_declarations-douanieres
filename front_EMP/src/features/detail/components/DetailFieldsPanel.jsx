import { useMemo, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

/**
 * @param {{ sections: Array<{ section: string, fields: Array<{ key: string, label: string, value: string, confidence?: number|null }> }>, title?: string }} props
 */
function DetailFieldsPanel({ sections, title = 'Champs extraits' }) {
	const [showEmpty, setShowEmpty] = useState(false);

	const visibleSections = useMemo(() => {
		if (showEmpty) {
			return sections;
		}
		return sections
			.map((s) => ({
				...s,
				fields: s.fields.filter((f) => f.value != null && String(f.value).trim() !== ''),
			}))
			.filter((s) => s.fields.length > 0);
	}, [sections, showEmpty]);

	const totalShown = visibleSections.reduce((n, s) => n + s.fields.length, 0);

	return (
		<section className="card-panel detail-fields-panel">
			<div className="detail-fields-panel-head">
				<h2>{title}</h2>
				<button
					type="button"
					className="detail-toggle-empty"
					onClick={() => setShowEmpty((v) => !v)}
				>
					{showEmpty ? <EyeOff size={16} /> : <Eye size={16} />}
					{showEmpty ? 'Masquer les champs vides' : 'Afficher aussi les champs vides'}
				</button>
			</div>
			<p className="detail-fields-count">
				{totalShown} champ{totalShown > 1 ? 's' : ''} affiché{totalShown > 1 ? 's' : ''}
			</p>
			{visibleSections.length === 0 ? (
				<p className="detail-empty-tab">Aucun champ extrait à afficher.</p>
			) : (
				<div className="detail-section-grid">
					{visibleSections.map((section) => (
						<div key={section.section} className="detail-section-card">
							<div className="detail-section-head">
								<div>
									<p className="detail-section-kicker">Section</p>
									<h3>{section.section}</h3>
								</div>
								<span className="detail-section-badge">{section.fields.length}</span>
							</div>
							<div className="detail-fields-grid">
								{section.fields.map((field) => (
									<div key={field.key || field.id} className="detail-field-item">
										<span>{field.label}</span>
										<strong className={field.isJson ? 'detail-field-json' : ''}>
											{field.value || '—'}
										</strong>
										{field.confidence != null ? (
											<small className="detail-field-conf">OCR {field.confidence}%</small>
										) : null}
									</div>
								))}
							</div>
						</div>
					))}
				</div>
			)}
		</section>
	);
}

export default DetailFieldsPanel;
