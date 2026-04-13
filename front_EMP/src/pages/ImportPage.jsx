import { useState } from 'react';
import { AlertTriangle, CheckCircle2, FileBadge2, ShieldCheck, Sparkles, Upload } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import DropZone from '../components/Import/DropZone';
import FilePreview from '../components/Import/FilePreview';
import FileTypeSelector from '../components/Import/FileTypeSelector';
import UploadProgress from '../components/Import/UploadProgress';
import { extractOcrDocument } from '../services/ocrService';
import { DEFAULT_DOCUMENT_ID, mapBackendResultToFields } from '../utils/ocrFields';

const fileTypeOptions = [
	{
		id: 'declaration',
		label: 'Declaration douaniere',
		description: 'Extrait les codes, taxes et champs reglementaires',
		badge: 'Recommande',
	},
	{
		id: 'invoice',
		label: 'Facture commerciale',
		description: 'Capture vendeur, client et details de lignes',
		badge: 'Nouveau',
	},
	
];

const readFileAsDataUrl = (file) =>
	new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(reader.result);
		reader.onerror = () => reject(new Error('Impossible de lire le document.'));
		reader.readAsDataURL(file);
	});

const buildDocumentId = (backendResult) => {
	if (backendResult?.numero_declaration) {
		return backendResult.numero_declaration;
	}
	if (backendResult?.id) {
		const year = new Date().getFullYear();
		const serial = String(backendResult.id).padStart(4, '0');
		return `INV-${year}-${serial}`;
	}
	return DEFAULT_DOCUMENT_ID;
};

function ImportPage() {
	const navigate = useNavigate();
	const [selectedFile, setSelectedFile] = useState(null);
	const [selectedType, setSelectedType] = useState(fileTypeOptions[0].id);
	const [uploadStatus, setUploadStatus] = useState('idle');
	const [uploadProgress, setUploadProgress] = useState(0);
	const [errorMessage, setErrorMessage] = useState('');

	const handleFileDrop = (file) => {
		setSelectedFile(file);
		setUploadStatus('ready');
		setUploadProgress(0);
		setErrorMessage('');
	};

	const handleRemoveFile = () => {
		setSelectedFile(null);
		setUploadStatus('idle');
		setUploadProgress(0);
		setErrorMessage('');
	};

	const startUpload = async () => {
		if (!selectedFile) {
			return;
		}

		setUploadStatus('uploading');
		setUploadProgress(0);
		setErrorMessage('');

		try {
			const dataUrl = await readFileAsDataUrl(selectedFile);
			const source = {
				name: selectedFile.name,
				type: selectedFile.type,
				size: selectedFile.size,
				lastModified: selectedFile.lastModified,
				dataUrl,
			};
			localStorage.setItem('ocr_uploaded_document', JSON.stringify(source));

			const result = await extractOcrDocument(selectedFile, {
				onUploadProgress: (event) => {
					if (event.total) {
						const percent = Math.round((event.loaded / event.total) * 100);
						setUploadProgress(Math.max(5, Math.min(percent, 95)));
					}
				},
			});

			const documentId = buildDocumentId(result);
			const fields = mapBackendResultToFields(result);

			localStorage.setItem(
				'ocr_latest_result',
				JSON.stringify({
					documentId,
					backendId: result?.id ?? null,
					fields,
					rawResult: result,
					source,
					selectedType,
					savedAt: new Date().toISOString(),
				})
			);

			setUploadProgress(100);
			setUploadStatus('completed');

			window.setTimeout(() => {
				navigate('/ocr-result');
			}, 300);
		} catch (error) {
			setUploadStatus('error');
			setUploadProgress(0);
			const detail = error?.response?.data?.detail;
			const message =
				typeof detail === 'string'
					? detail
					: detail?.message || detail?.error || "L'envoi vers OCR a echoue.";
			setErrorMessage(message);
		}
	};

	const isUploading = uploadStatus === 'uploading';
	const statusLabelMap = {
		idle: 'En attente de document',
		ready: 'Pret a envoyer',
		uploading: 'Envoi en cours',
		completed: 'Document traite',
		error: 'Erreur de traitement',
	};

	const statusDetailMap = {
		idle: 'Ajoutez un fichier pour demarrer le flux OCR.',
		ready: 'Verifiez les informations puis lancez l\'envoi.',
		uploading: 'Le document est envoye puis extrait par le backend OCR.',
		completed: 'Extraction terminee. Redirection vers les resultats OCR.',
		error: 'Une erreur est survenue pendant l\'envoi.',
	};

	const workflowSteps = [
		{ label: 'Choix du type de document', state: selectedType ? 'done' : 'pending' },
		{ label: 'Ajout du fichier source', state: selectedFile ? 'done' : 'pending' },
		{
			label: 'Transmission vers OCR',
			state:
				uploadStatus === 'uploading'
					? 'active'
					: uploadStatus === 'completed'
						? 'done'
						: 'pending',
		},
		{ label: 'Extraction et verification', state: uploadStatus === 'completed' ? 'done' : 'pending' },
	];

	const visualProgress =
		uploadStatus === 'ready'
			? 18
			: uploadStatus === 'idle'
				? 0
				: uploadStatus === 'completed'
					? 100
					: uploadProgress;

	return (
		<div className="import-page-container modern-import">
			<section className="dashboard-hero modern import-hero-modern fade-up">
				<div>
					<p className="hero-pill">Flux OCR</p>
					<h1>Import de documents</h1>
					<p className="subtitle">
						Deposez vos fichiers, lancez l&apos;analyse OCR et suivez l&apos;avancement en direct dans une interface
						claire.
					</p>
				</div>
				<div className="import-hero-badges">
					<span className="import-hero-chip">
						<FileBadge2 size={14} /> PDF, JPG, PNG
					</span>
					<span className="import-hero-chip">
						<ShieldCheck size={14} /> Donnees securisees
					</span>
				</div>
			</section>

			<div className="import-modern-layout fade-up">
				<section className="import-panel import-modern-panel">
					<div className="import-panel-head">
						<p className="import-panel-kicker">Etape 1</p>
						<h2>Preparation du document</h2>
					</div>

					<FileTypeSelector
						options={fileTypeOptions}
						value={selectedType}
						onChange={setSelectedType}
					/>
					<DropZone onFileDrop={handleFileDrop} disabled={isUploading} />
					<FilePreview file={selectedFile} onRemove={handleRemoveFile} />
					<UploadProgress progress={uploadProgress} status={uploadStatus} />

					<button
						type="button"
						className="auth-button import-submit"
						onClick={startUpload}
						disabled={!selectedFile || isUploading}
					>
						<Upload size={18} />
						{isUploading ? 'Envoi en cours...' : 'Envoyer vers OCR'}
					</button>

					{errorMessage && (
						<p className="profile-message is-error" style={{ marginTop: '0.8rem' }}>
							<AlertTriangle size={16} style={{ marginRight: '0.4rem', verticalAlign: 'text-bottom' }} />
							{errorMessage}
						</p>
					)}

					<p className="import-note">
						Connecte en tant qu&apos;utilisateur authentifie.{' '}
						<Link to="/login" className="auth-link">
							Changer de compte
						</Link>
					</p>
				</section>

				<aside className="import-modern-side">
					<section className="import-side-card">
						<p className="import-side-kicker">Suivi instantane</p>
						<h3>Etat du traitement</h3>
						<p className={`import-side-status ${uploadStatus}`}>{statusLabelMap[uploadStatus]}</p>
						<p className="import-side-detail">{statusDetailMap[uploadStatus]}</p>
						<div className="import-side-meter">
							<span style={{ width: `${visualProgress}%` }} />
						</div>
						<p className="import-side-percent">{Math.round(visualProgress)}%</p>
					</section>

					<section className="import-side-card">
						<p className="import-side-kicker">Workflow</p>
						<h3>Pipeline d&apos;import</h3>
						<div className="import-steps">
							{workflowSteps.map((step) => (
								<div key={step.label} className={`import-step ${step.state}`}>
									<span className="import-step-dot" aria-hidden="true" />
									<span>{step.label}</span>
									{step.state === 'done' ? <CheckCircle2 size={15} /> : null}
								</div>
							))}
						</div>
					</section>

					<section className="import-side-card import-side-tip">
						<Sparkles size={16} />
						<p>
							Pour une extraction plus fiable, privilegiez des scans lisibles avec contraste eleve.
						</p>
					</section>
				</aside>
			</div>
		</div>
	);
}

export default ImportPage;
