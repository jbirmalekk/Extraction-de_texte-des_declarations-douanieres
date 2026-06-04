import { CheckCircle2, ArrowRight, Database } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import {
	ERP_EXPORT,
	getErpSuccessMessage,
	getErpSuccessTitle,
} from '../utils/erpExport';
import './ErpSuccessPage.css';

function ErpSuccessPage() {
	const location = useLocation();
	const erp = location.state?.erpExport;
	const kind = erp?.kind || ERP_EXPORT.DUM;
	const title = getErpSuccessTitle(kind);
	const message = getErpSuccessMessage(kind, erp?.reference, erp?.erpReference);

	return (
		<div className="erp-success-page fade-up">
			<section className="erp-success-card">
				<div className="erp-success-icon-wrap">
					<Database size={28} className="erp-success-icon-muted" />
					<CheckCircle2 size={52} className="erp-success-icon-ok" />
				</div>
				<h1>{title}</h1>
				<p className="erp-success-message">{message}</p>
				{erp?.exportId ? (
					<p className="erp-success-meta">
						Enregistrement S1 (OCR) : export #{erp.exportId}
						{erp?.erpReference ? ` · ${erp.erpReference}` : ''}
					</p>
				) : null}
				{erp?.migrationMessage ? (
					<p className="erp-success-hint">{erp.migrationMessage}</p>
				) : (
					<p className="erp-success-hint">
						Données enregistrées sur le serveur OCR (S1), puis migration via le serveur ERP
						(S2). Remplacez l’URL S2 par le système Uniges en production.
					</p>
				)}
				{erp?.exportedAt ? (
					<p className="erp-success-meta">
						Horodatage : {new Date(erp.exportedAt).toLocaleString('fr-FR')}
					</p>
				) : null}
				<div className="erp-success-actions">
					<Link to="/history" className="erp-success-btn ghost">
						Historique
					</Link>
					{kind === ERP_EXPORT.DOSSIER && erp?.invoiceId ? (
						<Link to={`/reports/${erp.invoiceId}`} className="erp-success-btn ghost">
							Voir le rapport
						</Link>
					) : null}
					<Link to="/import" className="erp-success-btn primary">
						Nouveau document <ArrowRight size={14} />
					</Link>
				</div>
			</section>
		</div>
	);
}

export default ErpSuccessPage;
