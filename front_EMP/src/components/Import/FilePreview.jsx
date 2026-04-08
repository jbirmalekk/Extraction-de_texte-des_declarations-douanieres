function formatSize(sizeInBytes) {
	if (!sizeInBytes && sizeInBytes !== 0) {
		return '—';
	}
	if (sizeInBytes < 1024) {
		return `${sizeInBytes} B`;
	}
	if (sizeInBytes < 1024 * 1024) {
		return `${(sizeInBytes / 1024).toFixed(1)} KB`;
	}
	return `${(sizeInBytes / (1024 * 1024)).toFixed(2)} MB`;
}

function FilePreview({ file, onRemove }) {
	if (!file) {
		return null;
	}

	return (
		<div className="file-preview">
			<div className="file-preview-info">
				<div className="file-preview-icon">📁</div>
				<div>
					<p className="file-preview-name">{file.name}</p>
					<p className="file-preview-meta">
						{file.type || 'Unknown type'} · {formatSize(file.size)}
					</p>
				</div>
			</div>
			<button type="button" className="file-remove" onClick={onRemove}>
				Retirer
			</button>
		</div>
	);
}

export default FilePreview;
