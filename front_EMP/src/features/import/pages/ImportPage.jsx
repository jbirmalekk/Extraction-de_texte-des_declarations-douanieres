import { useEffect, useState } from 'react';
import {
	AlertTriangle,
	CheckCircle2,
	FileBadge2,
	Loader2,
	ShieldCheck,
	Sparkles,
	Upload,
	XCircle,
} from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import DropZone from '@/features/import/components/DropZone';
import FilePreview from '@/features/import/components/FilePreview';
import FileTypeSelector from '@/features/import/components/FileTypeSelector';
import ImageCropper from '@/features/import/components/ImageCropper';
import UploadProgress from '@/features/import/components/UploadProgress';
import {
	looksLikeDumFileName,
	looksLikeInvoiceFileName,
} from '@/shared/utils/extractionRouting';
import { markCrossVerifyImportReturn } from '@/shared/utils/crossVerificationSession';
import { useExtractionJobs } from '@/shared/store/ExtractionJobsContext';

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

const fileFingerprint = (file) => `${file.name}::${file.size}::${file.lastModified}`;

const mergeSelectedFiles = (existing, incoming) => {
	const map = new Map();
	existing.forEach((file) => map.set(fileFingerprint(file), file));
	incoming.forEach((file) => map.set(fileFingerprint(file), file));
	return Array.from(map.values());
};

const jobStatusLabel = {
	pending: 'En attente',
	processing: 'Extraction…',
	done: 'Terminé',
	error: 'Erreur',
};

function ExtractionRunningView({ extraction }) {
	const doneCount = extraction.jobs.filter((j) => j.status === 'done').length;
	const errorCount = extraction.jobs.filter((j) => j.status === 'error').length;

	return (
		<div className="import-page-container modern-import">
			<section className="dashboard-hero modern import-hero-modern fade-up">
				<div>
					<p className="hero-pill">Flux OCR</p>
					<h1>Extraction en cours</h1>
					<p className="subtitle">
						L&apos;extraction de {extraction.total} document{extraction.total > 1 ? 's' : ''} est en cours.
						Vous pouvez naviguer vers d&apos;autres pages : le traitement continue et vous serez redirigé
						automatiquement à la fin.
					</p>
				</div>
				<div className="import-hero-badges">
					<span className="import-hero-chip">
						<Loader2 size={14} className="spin" /> {doneCount}/{extraction.total} traités
					</span>
					{errorCount > 0 ? (
						<span className="import-hero-chip">
							<AlertTriangle size={14} /> {errorCount} erreur{errorCount > 1 ? 's' : ''}
						</span>
					) : null}
				</div>
			</section>

			<div className="import-modern-layout fade-up">
				<section className="import-panel import-modern-panel">
					<div className="import-panel-head">
						<p className="import-panel-kicker">Traitement</p>
						<h2>Progression de l&apos;extraction</h2>
					</div>

					<UploadProgress
						progress={extraction.progress}
						status="uploading"
						detail={extraction.detail}
					/>

					<div className="import-jobs-list">
						{extraction.jobs.map((job, index) => (
							<div key={`${job.fileName}-${index}`} className={`import-job-row ${job.status}`}>
								<span className="import-job-icon" aria-hidden="true">
									{job.status === 'done' ? (
										<CheckCircle2 size={16} />
									) : job.status === 'error' ? (
										<XCircle size={16} />
									) : job.status === 'processing' ? (
										<Loader2 size={16} className="spin" />
									) : (
										<span className="import-step-dot" />
									)}
								</span>
								<span className="import-job-name">{job.fileName}</span>
								<span className={`import-job-status ${job.status}`}>
									{jobStatusLabel[job.status] || job.status}
								</span>
							</div>
						))}
					</div>

					<p className="import-note">
						Astuce : ouvrez l&apos;<Link to="/history" className="auth-link">historique</Link> ou une autre page
						pendant l&apos;extraction — cette progression restera visible en revenant ici.
					</p>
				</section>

				<aside className="import-modern-side">
					<section className="import-side-card">
						<p className="import-side-kicker">Suivi instantane</p>
						<h3>Etat du traitement</h3>
						<p className="import-side-status uploading">Extraction en cours</p>
						<p className="import-side-detail">{extraction.detail}</p>
						<div className="import-side-meter">
							<span style={{ width: `${extraction.progress}%` }} />
						</div>
						<p className="import-side-percent">{Math.round(extraction.progress)}%</p>
					</section>

					<section className="import-side-card import-side-tip">
						<Sparkles size={16} />
						<p>
							À la fin, vous serez redirigé vers{' '}
							{extraction.isBatch ? 'la liste des documents extraits' : 'la page de résultats'} pour lancer
							la vérification.
						</p>
					</section>
				</aside>
			</div>
		</div>
	);
}

function ImportPage() {
	const [searchParams] = useSearchParams();
	const extraction = useExtractionJobs();
	const returnToCrossVerify = searchParams.get('returnTo') === 'cross-verification';
	const [selectedFiles, setSelectedFiles] = useState([]);
	const [selectedType, setSelectedType] = useState(fileTypeOptions[0].id);
	const [errorMessage, setErrorMessage] = useState('');
	const [activeCropKey, setActiveCropKey] = useState(null);
	const [activeCropImageUrl, setActiveCropImageUrl] = useState('');
	const [croppedFilesByKey, setCroppedFilesByKey] = useState({});

	const croppedFileKeys = Object.keys(croppedFilesByKey);
	const activeCropFile = selectedFiles.find((file) => fileFingerprint(file) === activeCropKey);

	useEffect(() => {
		let objectUrl = '';
		if (activeCropKey && activeCropFile?.type?.startsWith('image/')) {
			objectUrl = URL.createObjectURL(activeCropFile);
			setActiveCropImageUrl(objectUrl);
		} else {
			setActiveCropImageUrl('');
		}
		return () => {
			if (objectUrl) {
				URL.revokeObjectURL(objectUrl);
			}
		};
	}, [activeCropKey, activeCropFile]);

	useEffect(() => {
		const docType = searchParams.get('docType');
		if (docType === 'invoice' || docType === 'declaration') {
			setSelectedType(docType);
		}
		if (returnToCrossVerify) {
			const partnerKind = docType === 'invoice' ? 'invoice' : 'dum';
			markCrossVerifyImportReturn(partnerKind);
		}
	}, [searchParams, returnToCrossVerify]);

	const handleFileDrop = (files) => {
		const normalizedFiles = Array.isArray(files) ? files : files ? [files] : [];
		if (!normalizedFiles.length) {
			return;
		}
		const firstName = normalizedFiles[0]?.name || '';
		if (looksLikeInvoiceFileName(firstName) && !looksLikeDumFileName(firstName)) {
			setSelectedType('invoice');
		} else if (looksLikeDumFileName(firstName) && !looksLikeInvoiceFileName(firstName)) {
			setSelectedType('declaration');
		}
		setSelectedFiles((prev) => mergeSelectedFiles(prev, normalizedFiles));
		setErrorMessage('');
	};

	const handleSelectFileForCrop = (index) => {
		const file = selectedFiles[index];
		if (!file) {
			return;
		}
		if (!file.type?.startsWith('image/')) {
			setErrorMessage('Le cadrage est disponible uniquement pour les images (JPG, PNG).');
			return;
		}
		setErrorMessage('');
		setActiveCropKey(fileFingerprint(file));
	};

	const handleCropApplied = ({ croppedFile: nextCroppedFile, error }) => {
		if (error) {
			setErrorMessage(error.message || "Impossible d'appliquer le decoupage.");
			return;
		}
		if (!nextCroppedFile || !activeCropKey) {
			return;
		}
		setCroppedFilesByKey((prev) => ({
			...prev,
			[activeCropKey]: nextCroppedFile,
		}));
		setErrorMessage('');
	};

	const handleRemoveFile = () => {
		setSelectedFiles([]);
		setActiveCropKey(null);
		setCroppedFilesByKey({});
		setErrorMessage('');
	};

	const handleRemoveFileAt = (indexToRemove) => {
		const removed = selectedFiles[indexToRemove];
		const removedKey = removed ? fileFingerprint(removed) : null;

		setSelectedFiles((prev) => prev.filter((_, idx) => idx !== indexToRemove));

		if (removedKey) {
			setCroppedFilesByKey((prev) => {
				const next = { ...prev };
				delete next[removedKey];
				return next;
			});
			if (activeCropKey === removedKey) {
				setActiveCropKey(null);
			}
		}
	};

	const startUpload = () => {
		if (!selectedFiles.length) {
			return;
		}
		if (returnToCrossVerify && selectedFiles.length > 1) {
			setErrorMessage('La réconciliation accepte un seul document à la fois.');
			return;
		}

		let uploadDocumentType = selectedType;
		const primaryFile = selectedFiles[0];
		if (
			uploadDocumentType === 'declaration' &&
			looksLikeInvoiceFileName(primaryFile?.name) &&
			!looksLikeDumFileName(primaryFile?.name)
		) {
			const useInvoice = window.confirm(
				'Ce fichier ressemble a une facture commerciale.\n\n' +
					'OK = extraire en mode Facture (formulaire facture)\n' +
					'Annuler = garder le mode Declaration DUM'
			);
			if (useInvoice) {
				uploadDocumentType = 'invoice';
				setSelectedType('invoice');
			}
		}

		setErrorMessage('');
		extraction.startExtraction({
			files: selectedFiles,
			croppedFilesByKey,
			uploadDocumentType,
			returnToCrossVerify,
		});
	};

	// Extraction globale en cours : afficher la vue de progression, même en revenant sur la page.
	if (extraction.status === 'running') {
		return <ExtractionRunningView extraction={extraction} />;
	}

	const isInvoiceType = selectedType === 'invoice';
	const isSingleFile = selectedFiles.length === 1;
	const displayError = errorMessage || (extraction.status === 'error' ? extraction.error : '');
	const formStatus = selectedFiles.length ? 'ready' : 'idle';
	const resultsLabel = isInvoiceType ? 'Resultats facture' : 'Resultats DUM';
	const statusLabelMap = {
		idle: 'En attente de document',
		ready: 'Pret a envoyer',
	};
	const statusDetailMap = {
		idle: 'Ajoutez un fichier pour demarrer le flux OCR.',
		ready: isSingleFile
			? `1 document pret — apres extraction, redirection automatique vers ${resultsLabel}.`
			: `${selectedFiles.length} documents — apres extraction, page Resultats de lot.`,
	};

	const workflowSteps = [
		{ label: 'Choix du type de document', state: selectedType ? 'done' : 'pending' },
		{ label: 'Ajout du fichier source', state: selectedFiles.length ? 'done' : 'pending' },
		{ label: 'Transmission vers OCR', state: 'pending' },
		{ label: 'Extraction et verification', state: 'pending' },
	];

	const visualProgress = formStatus === 'ready' ? 18 : 0;

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

			{returnToCrossVerify ? (
				<p className="import-return-banner fade-up">
					Extraction pour la <strong>réconciliation DUM vs Facture</strong> — après traitement, vous
					reviendrez à la sélection du document partenaire.
					<Link to="/cross-verification"> Annuler et retour réconciliation</Link>
				</p>
			) : null}

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
					<p className={`import-type-hint ${selectedType}`}>
						{selectedType === 'invoice' ? (
							<>
								<strong>Facture commerciale</strong> — apres extraction, vous serez redirige vers{' '}
								<strong>Resultats facture</strong>.
							</>
						) : (
							<>
								<strong>Declaration DUM</strong> — apres extraction, vous serez redirige vers{' '}
								<strong>Resultats DUM</strong>.
							</>
						)}
					</p>
					<DropZone onFileDrop={handleFileDrop} disabled={false} multiple />
					{selectedFiles.length > 0 ? (
						<p className="import-type-hint">
							{selectedFiles.length === 1 ? (
								<>
									1 fichier pret — apres extraction, redirection automatique vers{' '}
									<strong>{isInvoiceType ? 'Resultats facture' : 'Resultats DUM'}</strong>.
									{selectedFiles[0]?.type?.startsWith('image/')
										? ' Cliquez sur le fichier pour le cadrage personnalise.'
										: null}
								</>
							) : (
								<>
									{selectedFiles.length} fichiers prets — apres extraction, page{' '}
									<strong>Resultats de lot</strong>.
									{selectedFiles.some((f) => f.type?.startsWith('image/'))
										? ' Cliquez sur chaque image pour le cadrage.'
										: null}
								</>
							)}
						</p>
					) : null}
					<FilePreview
						files={selectedFiles}
						onRemove={handleRemoveFile}
						onRemoveAt={handleRemoveFileAt}
						onSelectFile={handleSelectFileForCrop}
						activeFileKey={activeCropKey}
						croppedFileKeys={croppedFileKeys}
						getFileKey={fileFingerprint}
					/>
					{croppedFileKeys.length > 0 ? (
						<p className="import-crop-success">
							<CheckCircle2 size={14} />
							{croppedFileKeys.length} image{croppedFileKeys.length > 1 ? 's' : ''} avec cadrage
							applique — envoi OCR avec rognage pour ces fichiers.
						</p>
					) : null}
					{activeCropKey && activeCropImageUrl && activeCropFile ? (
						<ImageCropper
							key={activeCropKey}
							imageUrl={activeCropImageUrl}
							sourceFile={activeCropFile}
							fileLabel={activeCropFile.name}
							disabled={false}
							onCropApplied={handleCropApplied}
						/>
					) : null}

					<button
						type="button"
						className="auth-button import-submit"
						onClick={startUpload}
						disabled={!selectedFiles.length}
					>
						<Upload size={18} />
						{selectedFiles.length > 1
							? `Lancer l'extraction (${selectedFiles.length} fichiers)`
							: "Lancer l'extraction"}
					</button>

					{displayError && (
						<p className="profile-message is-error" style={{ marginTop: '0.8rem' }}>
							<AlertTriangle size={16} style={{ marginRight: '0.4rem', verticalAlign: 'text-bottom' }} />
							{displayError}
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
						<p className={`import-side-status ${formStatus}`}>{statusLabelMap[formStatus]}</p>
						<p className="import-side-detail">{statusDetailMap[formStatus]}</p>
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
