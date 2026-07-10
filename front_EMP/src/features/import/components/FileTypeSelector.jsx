function FileTypeSelector({ options, value, onChange }) {
	return (
		<div className="file-type-selector">
			<p className="selector-label">Choisissez le type de document</p>
			<div className="selector-grid">
				{options.map((option) => (
					<button
						key={option.id}
						type="button"
						className={`selector-tile ${value === option.id ? 'active' : ''}`}
						onClick={() => onChange(option.id)}
					>
						<div className="selector-badge">{option.badge}</div>
						<p className="selector-title">{option.label}</p>
						<p className="selector-description">{option.description}</p>
					</button>
				))}
			</div>
		</div>
	);
}

export default FileTypeSelector;
