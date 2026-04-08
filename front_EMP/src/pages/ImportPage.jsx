import { useEffect, useRef, useState } from 'react';
import { Upload } from 'lucide-react';
import { Link } from 'react-router-dom';
import DropZone from '../components/Import/DropZone';
import FilePreview from '../components/Import/FilePreview';
import FileTypeSelector from '../components/Import/FileTypeSelector';
import UploadProgress from '../components/Import/UploadProgress';

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
	{
		id: 'manifest',
		label: 'Manifeste cargo',
		description: 'Consolide les expeditions en un seul flux',
		badge: 'Logistique',
	},
];

function ImportPage() {
	const [selectedFile, setSelectedFile] = useState(null);
	const [selectedType, setSelectedType] = useState(fileTypeOptions[0].id);
	const [uploadStatus, setUploadStatus] = useState('idle');
	const [uploadProgress, setUploadProgress] = useState(0);
	const uploadIntervalRef = useRef(null);

	useEffect(() => {
		return () => {
			if (uploadIntervalRef.current) {
				clearInterval(uploadIntervalRef.current);
			}
		};
	}, []);

	const handleFileDrop = (file) => {
		setSelectedFile(file);
		setUploadStatus('ready');
		setUploadProgress(0);
		if (uploadIntervalRef.current) {
			clearInterval(uploadIntervalRef.current);
			uploadIntervalRef.current = null;
		}
	};

	const handleRemoveFile = () => {
		setSelectedFile(null);
		setUploadStatus('idle');
		setUploadProgress(0);
		if (uploadIntervalRef.current) {
			clearInterval(uploadIntervalRef.current);
			uploadIntervalRef.current = null;
		}
	};

	const startUpload = () => {
		if (!selectedFile) {
			return;
		}
		setUploadStatus('uploading');
		setUploadProgress(0);
		if (uploadIntervalRef.current) {
			clearInterval(uploadIntervalRef.current);
		}
		uploadIntervalRef.current = window.setInterval(() => {
			setUploadProgress((prev) => {
				if (prev >= 100) {
					clearInterval(uploadIntervalRef.current);
					uploadIntervalRef.current = null;
					setUploadStatus('completed');
					return 100;
				}
				return prev + 15;
			});
		}, 350);
	};

	const isUploading = uploadStatus === 'uploading';

	return (
		<div className="import-page-container">
			<section className="import-head">
				<p className="import-head-kicker">Import intelligent</p>
				<h1>Importer un document</h1>
				<p>
					Selectionnez le type de document puis lancez l&apos;envoi vers l&apos;OCR pour extraction automatique.
				</p>
			</section>

			<div className="import-page">
				<section className="import-panel">
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
						disabled={!selectedFile || isUploading || uploadStatus === 'completed'}
					>
						<Upload size={18} />
						{isUploading ? 'Envoi en cours...' : 'Envoyer vers OCR'}
					</button>
					<p className="import-note">
						Connecte en tant qu&apos;utilisateur authentifie.{' '}
						<Link to="/login" className="auth-link">
							Changer de compte
						</Link>
					</p>
				</section>
			</div>
		</div>
	);
}

export default ImportPage;
