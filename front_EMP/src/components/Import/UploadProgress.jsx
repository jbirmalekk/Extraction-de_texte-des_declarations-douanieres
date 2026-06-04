function UploadProgress({ progress, status, detail }) {
	if (status === 'idle') {
		return null;
	}

	const statusLabel = {
		uploading: 'Envoi en cours',
		completed: 'Envoi termine',
		error: 'Echec de l\'envoi',
		ready: 'Pret pour l\'envoi',
	}[status] || 'Traitement';

	return (
		<div className={`upload-progress ${status}`}>
			<div className="upload-progress-header">
				<span>{statusLabel}</span>
				<span>{Math.round(progress)}%</span>
			</div>
			{detail ? <p className="upload-progress-detail">{detail}</p> : null}
			<div className="upload-progress-bar">
				<div className="upload-progress-value" style={{ width: `${progress}%` }} />
			</div>
		</div>
	);
}

export default UploadProgress;
