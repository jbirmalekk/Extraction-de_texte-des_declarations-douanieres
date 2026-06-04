import { useState } from 'react';
import { FileText, ZoomIn, ZoomOut } from 'lucide-react';
import { useDocumentFilePreview } from '../../hooks/useDocumentFilePreview';
import { resolveStoredDocumentPreview } from '../../utils/compareDocumentPreview';
import './DetailDocumentPreview.css';

function DetailDocumentPreview({
	kind,
	documentId,
	fileName,
	contentType,
	dossier,
	title = 'Aperçu du document',
}) {
	const [zoom, setZoom] = useState(100);
	const numericId = Number(documentId);
	const storedPreview = resolveStoredDocumentPreview(kind, numericId);

	const { preview, loading, error } = useDocumentFilePreview({
		kind,
		entityId: Number.isFinite(numericId) && numericId > 0 ? numericId : null,
		payloadSource: storedPreview,
		fileName,
		contentType,
		dossier,
		storageKey: kind === 'invoice' ? 'invoice_uploaded_document' : 'ocr_uploaded_document',
	});

	const isPdf = Boolean(preview?.type?.toLowerCase().includes('pdf'));
	const hasPreview = Boolean(preview?.dataUrl);

	return (
		<section className="card-panel detail-doc-preview">
			<div className="detail-doc-preview-head">
				<h2>{title}</h2>
				<div className="detail-doc-preview-controls">
					<button
						type="button"
						onClick={() => setZoom((z) => Math.max(z - 25, 50))}
						disabled={!hasPreview}
						aria-label="Zoom arrière"
					>
						<ZoomOut size={16} />
					</button>
					<span>{zoom}%</span>
					<button
						type="button"
						onClick={() => setZoom((z) => Math.min(z + 25, 200))}
						disabled={!hasPreview}
						aria-label="Zoom avant"
					>
						<ZoomIn size={16} />
					</button>
				</div>
			</div>
			<div className="detail-doc-preview-viewport">
				{hasPreview ? (
					<div className="detail-doc-preview-inner" style={{ width: `${zoom}%` }}>
						{isPdf ? (
							<iframe
								title={preview.name || title}
								src={preview.dataUrl}
								className="detail-doc-preview-pdf"
							/>
						) : (
							<img
								src={preview.dataUrl}
								alt={preview.name || title}
								className="detail-doc-preview-img"
							/>
						)}
					</div>
				) : (
					<div className="detail-doc-preview-empty">
						<FileText size={40} />
						<p>
							{loading
								? 'Chargement de l\u2019aperçu…'
								: 'Aperçu non disponible (document non importé sur cet appareil ou session expirée).'}
						</p>
						{error ? <p className="detail-doc-preview-hint">{error}</p> : null}
						{!loading && !error ? (
							<p className="detail-doc-preview-hint">
								Si le document est en base avec un chemin GED, l&apos;aperçu est récupéré depuis
								Nextcloud.
							</p>
						) : null}
					</div>
				)}
			</div>
		</section>
	);
}

export default DetailDocumentPreview;
