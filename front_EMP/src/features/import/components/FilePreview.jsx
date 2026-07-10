import { CheckCircle2, Crop } from 'lucide-react';

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

function FilePreview({
	file,
	files,
	onRemove,
	onRemoveAt,
	onSelectFile,
	activeFileKey,
	croppedFileKeys = [],
	getFileKey,
}) {
	const list = Array.isArray(files) ? files : file ? [file] : [];
	if (!list.length) {
		return null;
	}

	const resolveKey = getFileKey || ((item) => `${item.name}::${item.size}::${item.lastModified}`);
	const croppedSet = new Set(croppedFileKeys);

	return (
		<div className="file-preview">
			<div className="file-preview-list">
				{list.map((item, index) => {
					const fileKey = resolveKey(item);
					const isImage = item.type?.startsWith('image/');
					const isActive = activeFileKey === fileKey;
					const isCropped = croppedSet.has(fileKey);

					return (
						<div
							key={`${fileKey}-${index}`}
							className={`file-preview-info ${isImage ? 'is-selectable' : ''} ${isActive ? 'is-active-crop' : ''}`}
						>
							{isImage && onSelectFile ? (
								<button
									type="button"
									className="file-preview-select"
									onClick={() => onSelectFile(index)}
									aria-pressed={isActive}
								>
									<div className="file-preview-icon">{isCropped ? '✓' : '🖼️'}</div>
									<div className="file-preview-copy">
										<p className="file-preview-name">{item.name}</p>
										<p className="file-preview-meta">
											{item.type || 'Unknown type'} · {formatSize(item.size)}
										</p>
										<p className="file-preview-hint">
											{isActive ? (
												<span className="file-preview-hint-active">
													<Crop size={12} /> Cadrage en cours
												</span>
											) : isCropped ? (
												<span className="file-preview-hint-done">
													<CheckCircle2 size={12} /> Cadrage applique — cliquer pour modifier
												</span>
											) : (
												'Cliquer pour cadrer ce document'
											)}
										</p>
									</div>
								</button>
							) : (
								<>
									<div className="file-preview-icon">📁</div>
									<div className="file-preview-copy">
										<p className="file-preview-name">{item.name}</p>
										<p className="file-preview-meta">
											{item.type || 'Unknown type'} · {formatSize(item.size)}
										</p>
										<p className="file-preview-hint">PDF — pas de cadrage disponible</p>
									</div>
								</>
							)}
							{onRemoveAt ? (
								<button
									type="button"
									className="file-remove"
									onClick={(event) => {
										event.stopPropagation();
										onRemoveAt(index);
									}}
								>
									Retirer
								</button>
							) : null}
						</div>
					);
				})}
				{list.length > 1 ? <p className="file-preview-meta">{list.length} fichiers sélectionnés</p> : null}
				{list.length === 1 && onRemove && !onRemoveAt ? (
					<button type="button" className="file-remove file-remove-block" onClick={onRemove}>
						Retirer
					</button>
				) : null}
			</div>
		</div>
	);
}

export default FilePreview;
