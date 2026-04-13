import { useEffect, useState } from 'react';
import { CheckCircle2, FileWarning, Send } from 'lucide-react';
import { Link } from 'react-router-dom';
import { validateOcrDocument } from '../services/ocrService';
import { buildBackendValidationPayload } from '../utils/ocrFields';
import './ValidationPage.css';

const safeJsonParse = (value, fallback) => {
	if (!value) {
		return fallback;
	}
	try {
		return JSON.parse(value);
	} catch (_error) {
		return fallback;
	}
};

function ValidationPage() {
	const [payload, setPayload] = useState(null);
	const [status, setStatus] = useState('idle');
	const [message, setMessage] = useState('');

	useEffect(() => {
		const savedPayload = safeJsonParse(localStorage.getItem('ocr_validation_payload'), null);
		setPayload(savedPayload);
	}, []);

	const handleSendValidation = async () => {
		if (!payload) {
			return;
		}

		setStatus('loading');
		setMessage('');

		try {
			if (payload.backendId) {
				const backendPayload = buildBackendValidationPayload(payload.fields, payload.backendId, 'valide');
				await validateOcrDocument(payload.backendId, backendPayload);
			}

			const audit = {
				...payload,
				validatedAt: new Date().toISOString(),
			};
			localStorage.setItem('ocr_last_validated', JSON.stringify(audit));
			setStatus('success');
			setMessage(
				payload.backendId
					? 'Validation envoyee au backend avec succes.'
					: 'Validation sauvegardee localement.'
			);
		} catch (error) {
			setStatus('error');
			setMessage(error?.response?.data?.detail || 'Echec de validation, veuillez reessayer.');
		}
	};

	if (!payload) {
		return (
			<div className="validation-page fade-up">
				<section className="validation-card empty">
					<FileWarning size={24} />
					<h1>Aucune validation en attente</h1>
					<p>Commencez par importer un document et verifier vos resultats OCR.</p>
					<Link to="/import" className="validation-link-btn">
						Aller a l&apos;import
					</Link>
				</section>
			</div>
		);
	}

	const modifiedCount = Object.keys(payload.modifiedFields || {}).length;
	const fieldsCount = Array.isArray(payload.fields) ? payload.fields.length : 0;

	return (
		<div className="validation-page fade-up">
			<section className="validation-header">
				<div>
					<p className="validation-kicker">Validation finale</p>
					<h1>Controle des donnees OCR</h1>
				</div>
				<span className="validation-doc-id">{payload.documentId}</span>
			</section>

			<section className="validation-card">
				<div className="validation-summary">
					<div>
						<span>Champs totaux</span>
						<strong>{fieldsCount}</strong>
					</div>
					<div>
						<span>Champs modifies</span>
						<strong>{modifiedCount}</strong>
					</div>
					<div>
						<span>Lien backend</span>
						<strong>{payload.backendId ? `ID ${payload.backendId}` : 'Local only'}</strong>
					</div>
				</div>

				<div className="validation-actions">
					<button
						type="button"
						onClick={handleSendValidation}
						className="validation-send-btn"
						disabled={status === 'loading'}
					>
						{status === 'loading' ? 'Envoi...' : <Send size={16} />}
						{status === 'loading' ? '' : 'Envoyer la validation'}
					</button>
					<Link to="/ocr-result" className="validation-secondary-btn">
						Retour aux resultats
					</Link>
				</div>

				{message && (
					<p className={`validation-message ${status === 'success' ? 'success' : 'error'}`}>
						{status === 'success' ? <CheckCircle2 size={16} /> : <FileWarning size={16} />}
						{message}
					</p>
				)}
			</section>
		</div>
	);
}

export default ValidationPage;
