import { CheckCircle2, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

function ErpSuccessPage() {
	return (
		<div className="validation-page fade-up">
			<section className="validation-card" style={{ textAlign: 'center', padding: '2rem 1.2rem' }}>
				<CheckCircle2 size={56} color="#16a34a" style={{ marginBottom: '0.8rem' }} />
				<h1 style={{ margin: 0, color: '#0f172a' }}>Validation terminee avec succes</h1>
				<p style={{ margin: '0.7rem auto 1.2rem', maxWidth: '58ch', color: '#475569' }}>
					Le document est pret pour l'exportation ERP. Vous pouvez consulter l'historique ou continuer
					avec un nouveau document.
				</p>
				<div style={{ display: 'flex', gap: '0.7rem', justifyContent: 'center', flexWrap: 'wrap' }}>
					<Link to="/history" className="history-link-btn">
						Historique
					</Link>
					<Link to="/import" className="history-link-btn">
						Nouveau document <ArrowRight size={14} />
					</Link>
				</div>
			</section>
		</div>
	);
}

export default ErpSuccessPage;
