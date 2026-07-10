import { useState } from 'react';
import { ExternalLink, FileText, ZoomIn, ZoomOut } from 'lucide-react';
import { Link } from 'react-router-dom';

function DocumentPreviewPanel({
	title,
	subtitle,
	preview,
	editLink,
	editLabel,
	loading = false,
	error = '',
}) {
	const [zoom, setZoom] = useState(100);
	const isPdf = Boolean(preview?.type?.toLowerCase().includes('pdf'));
	const hasPreview = Boolean(preview?.dataUrl);

	return (
		<article className="cross-verify-preview-card">
			<header className="cross-verify-preview-head">
				<div>
					<p className="cross-verify-preview-tag">{title}</p>
					<h3>{subtitle}</h3>
				</div>
				{editLink ? (
					<Link to={editLink} className="cross-verify-preview-edit">
						<ExternalLink size={14} />
						{editLabel || 'Corriger'}
					</Link>
				) : null}
			</header>
			<div className="cross-verify-preview-toolbar">
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
			<div className="cross-verify-preview-viewport">
				{hasPreview ? (
					<div
						className="cross-verify-preview-inner"
						style={{ transform: `scale(${zoom / 100})` }}
					>
						{isPdf ? (
							<iframe title={preview.name || title} src={preview.dataUrl} className="cross-verify-preview-pdf" />
						) : (
							<img
								src={preview.dataUrl}
								alt={preview.name || title}
								className="cross-verify-preview-img"
							/>
						)}
					</div>
				) : (
					<div className="cross-verify-preview-empty">
						<FileText size={32} />
						<p>
							{loading
								? 'Chargement de l\u2019aperçu…'
								: 'Aperçu non disponible dans le navigateur.'}
						</p>
						{error ? (
							<p className="cross-verify-preview-empty-hint">{error}</p>
						) : (
							<p className="cross-verify-preview-empty-hint">
								{loading
									? 'Récupération du fichier depuis la GED (Nextcloud)…'
									: 'Rouvrez la validation ou réimportez le document pour afficher l\u2019image ici.'}
							</p>
						)}
					</div>
				)}
			</div>
			{preview?.name ? <p className="cross-verify-preview-filename">{preview.name}</p> : null}
		</article>
	);
}

export default DocumentPreviewPanel;
