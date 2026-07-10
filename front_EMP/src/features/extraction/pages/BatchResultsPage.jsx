import { useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
	AlertTriangle,
	CheckCircle2,
	FileText,
	FileUp,
	History,
	Layers,
	ReceiptText,
	RefreshCw,
	ArrowRight,
} from 'lucide-react';

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
	if (row.status !== 'Succes') {
		return false;
	}

	const snapshot = readBatchSnapshot(row.batchIndex);
	const isInvoice = row.type === 'Facture' || snapshot?.type === 'invoice';

	// Amorce le cache local si le snapshot a bien été sauvegardé (chemin rapide).
	if (snapshot) {
		if (snapshot.type === 'invoice') {
			persistJsonSafely('invoice_uploaded_document', snapshot.preview);
			persistJsonSafely('invoice_latest_result', snapshot.result);
		} else {
			persistJsonSafely('ocr_uploaded_document', snapshot.preview);
			persistJsonSafely('ocr_latest_result', snapshot.result);
		}
	}

	// Charge toujours depuis le backend via l'ID (fiable même si le snapshot a échoué).
	if (row.backendId != null) {
		return isInvoice
			? `/invoice-ocr-result?invoiceId=${row.backendId}`
			: `/ocr-result?documentId=${row.backendId}`;
	}

	if (!snapshot) {
		return false;
	}
	return isInvoice ? '/invoice-ocr-result' : '/ocr-result';
};

const formatDateTime = (iso) => {
	if (!iso) {
		return '';
	}
	try {
		return new Date(iso).toLocaleString('fr-FR', {
			day: '2-digit',
			month: '2-digit',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
		});
	} catch {
		return '';
	}
};

function BatchResultsPage() {
	const navigate = useNavigate();
	const batch = useMemo(() => readBatchResults(), []);

	if (!batch?.rows?.length) {
		return (
			<div className="import-page-container modern-import">
				<section className="dashboard-hero modern import-hero-modern fade-up">
					<div>
						<p className="hero-pill">Flux OCR</p>
						<h1>Documents extraits</h1>
						<p className="subtitle">
							Aucun lot d&apos;extraction récent. Importez plusieurs documents pour les retrouver ici et
							lancer leur vérification.
						</p>
					</div>
				</section>

				<div className="batch-empty fade-up">
					<Layers size={40} className="batch-empty__icon" />
					<h2>Aucun document extrait pour l&apos;instant</h2>
					<p>
						Lancez une extraction de plusieurs documents depuis la page Import. Le résultat du dernier lot
						s&apos;affichera ici.
					</p>
					<div className="batch-toolbar">
						<Link to="/import" className="batch-toolbar__btn batch-toolbar__btn--primary">
							<FileUp size={16} /> Aller à l&apos;import
						</Link>
						<Link to="/history" className="batch-toolbar__btn">
							<History size={16} /> Voir l&apos;historique
						</Link>
					</div>
				</div>
			</div>
		);
	}

	const rows = batch.rows;
	const successCount = rows.filter((row) => row.status === 'Succes').length;
	const errorCount = rows.length - successCount;
	const createdAtLabel = formatDateTime(batch.createdAt);

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
		<div className="import-page-container modern-import">
			<section className="dashboard-hero modern import-hero-modern fade-up">
				<div>
					<p className="hero-pill">Flux OCR</p>
					<h1>Documents extraits</h1>
					<p className="subtitle">
						{rows.length} document{rows.length > 1 ? 's' : ''} traité{rows.length > 1 ? 's' : ''} dans ce lot.
						Cliquez sur <strong>Vérifier</strong> pour contrôler et valider chaque document.
						{createdAtLabel ? ` · Lot du ${createdAtLabel}` : ''}
					</p>
				</div>
				<div className="import-hero-badges">
					<span className="import-hero-chip">
						<Layers size={14} /> {rows.length} au total
					</span>
					<span className="import-hero-chip">
						<CheckCircle2 size={14} /> {successCount} réussi{successCount > 1 ? 's' : ''}
					</span>
					{errorCount > 0 ? (
						<span className="import-hero-chip">
							<AlertTriangle size={14} /> {errorCount} en erreur
						</span>
					) : null}
				</div>
			</section>

			<div className="batch-toolbar fade-up">
				<Link to="/import" className="batch-toolbar__btn batch-toolbar__btn--primary">
					<RefreshCw size={16} /> Nouveau lot
				</Link>
				<Link to="/history" className="batch-toolbar__btn">
					<History size={16} /> Voir l&apos;historique
				</Link>
			</div>

			<div className="batch-table-wrap fade-up">
				<table className="batch-table">
					<thead>
						<tr>
							<th className="batch-table__col-num">#</th>
							<th>Fichier</th>
							<th>Type</th>
							<th>Statut</th>
							<th>Référence</th>
							<th className="batch-table__col-actions">Actions</th>
						</tr>
					</thead>
					<tbody>
						{rows.map((row, index) => {
							const isInvoice = row.type === 'Facture';
							const isSuccess = row.status === 'Succes';
							return (
								<tr key={row.id} className={isSuccess ? 'is-success' : 'is-error'}>
									<td className="batch-table__col-num">{index + 1}</td>
									<td className="batch-table__file">
										<FileText size={15} className="batch-table__file-icon" />
										<span title={row.fileName}>{row.fileName}</span>
									</td>
									<td>
										<span className={`batch-card__type ${isInvoice ? 'invoice' : 'dum'}`}>
											{isInvoice ? <ReceiptText size={14} /> : <FileText size={14} />}
											{row.type}
										</span>
									</td>
									<td>
										<span className={`status-pill ${isSuccess ? 'success' : 'danger'}`}>
											{isSuccess ? 'Extrait' : 'Erreur'}
										</span>
									</td>
									<td>
										{isSuccess ? (
											<span className="batch-table__ref">{row.documentId || '—'}</span>
										) : (
											<span className="batch-table__error" title={row.error || ''}>
												<AlertTriangle size={13} />
												{row.error || "L'extraction a échoué."}
											</span>
										)}
									</td>
									<td className="batch-table__col-actions">
										{isSuccess ? (
											<div className="batch-table__actions">
												<button
													type="button"
													className="batch-card__btn batch-card__btn--primary"
													onClick={() => handleOpenResult(row)}
												>
													Vérifier <ArrowRight size={15} />
												</button>
												{row.detailPath ? (
													<Link className="batch-card__btn" to={row.detailPath}>
														Fiche
													</Link>
												) : null}
											</div>
										) : (
											<Link className="batch-card__btn batch-card__btn--primary" to="/import">
												<RefreshCw size={15} /> Réessayer
											</Link>
										)}
									</td>
								</tr>
							);
						})}
					</tbody>
				</table>
			</div>
		</div>
	);
}

export default BatchResultsPage;
