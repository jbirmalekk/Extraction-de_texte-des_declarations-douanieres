import { Link, Navigate, useNavigate } from 'react-router-dom';

const readBatchResults = () => {
	try {
		return JSON.parse(localStorage.getItem('ocr_batch_results') || 'null');
	} catch {
		return null;
	}
};

const persistJsonSafely = (key, payload) => {
	try {
		localStorage.setItem(key, JSON.stringify(payload));
		return true;
	} catch {
		return false;
	}
};

const readBatchSnapshot = (batchIndex) => {
	try {
		const raw = sessionStorage.getItem(`ocr_batch_item_${batchIndex}`);
		return raw ? JSON.parse(raw) : null;
	} catch {
		return null;
	}
};

const openBatchExtractionResult = (row) => {
	const snapshot = readBatchSnapshot(row.batchIndex);
	if (!snapshot || row.status !== 'Succes') {
		return false;
	}

	if (snapshot.type === 'invoice') {
		persistJsonSafely('invoice_uploaded_document', snapshot.preview);
		persistJsonSafely('invoice_latest_result', snapshot.result);
		return '/invoice-ocr-result';
	}

	persistJsonSafely('ocr_uploaded_document', snapshot.preview);
	persistJsonSafely('ocr_latest_result', snapshot.result);
	return '/ocr-result';
};

function BatchResultsPage() {
	const navigate = useNavigate();
	const batch = readBatchResults();

	if (!batch?.rows?.length) {
		return <Navigate to="/import" replace />;
	}

	const successCount = batch.rows.filter((row) => row.status === 'Succes').length;
	const errorCount = batch.rows.length - successCount;

	const handleOpenResult = (row) => {
		const resultPath = openBatchExtractionResult(row);
		if (resultPath) {
			navigate(resultPath);
			return;
		}
		if (row.detailPath) {
			navigate(row.detailPath);
		}
	};

	return (
		<section className="activities">
			<div className="section-header">
				<h2>Resultats de lot</h2>
				<Link to="/import" className="text-link">
					Nouveau lot
				</Link>
			</div>
			<p className="subtitle" style={{ margin: '0 0 1rem' }}>
				{batch.rows.length} fichiers • {successCount} succes • {errorCount} erreurs
			</p>
			<div className="activity-table">
				<div className="table-head">
					<span>Fichier</span>
					<span>Type</span>
					<span>Statut</span>
					<span>Reference</span>
					<span>Action</span>
				</div>
				{batch.rows.map((row) => (
					<div key={row.id} className="table-row">
						<span>{row.fileName}</span>
						<span>{row.type}</span>
						<span>
							<span className={`status-pill ${row.status === 'Succes' ? 'success' : 'danger'}`}>
								{row.status}
							</span>
						</span>
						<span>{row.documentId || row.error || '—'}</span>
						<span style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
							{row.status === 'Succes' ? (
								<button type="button" className="table-action" onClick={() => handleOpenResult(row)}>
									Voir resultats OCR
								</button>
							) : null}
							{row.detailPath && row.status === 'Succes' ? (
								<Link className="table-action" to={row.detailPath}>
									Fiche document
								</Link>
							) : (
								<span className="table-action" aria-disabled="true">
									—
								</span>
							)}
						</span>
					</div>
				))}
			</div>
		</section>
	);
}

export default BatchResultsPage;
