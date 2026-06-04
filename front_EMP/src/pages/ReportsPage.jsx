import { useCallback, useEffect, useMemo, useState } from 'react';
import { Eye, GitCompare, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { fetchInvoicesList } from '../services/invoiceApi';
import { buildCompactDocParts } from '../utils/crossVerifyDisplay';
import { formatHistoryDateTime } from '../utils/historyUnified';

function ReportsDocCell({ numero, date }) {
	return (
		<span className="reports-doc-cell">
			<span className="reports-doc-num">{numero}</span>
			{date ? <span className="reports-doc-date">{date}</span> : null}
		</span>
	);
}
import './ReportsPage.css';

const controleLabel = (sc) => {
	if (sc === 'ok') {
		return 'Conforme';
	}
	if (sc === 'warning') {
		return 'Attention';
	}
	if (sc === 'error') {
		return 'Écart';
	}
	return '—';
};

function ReportsPage() {
	const { user } = useAuth();
	const [items, setItems] = useState([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState('');

	const loadReports = useCallback(async () => {
		setLoading(true);
		setError('');
		try {
			const page = await fetchInvoicesList({ limit: 200 }, user);
			const compared = (page.items || []).filter(
				(inv) => inv.compared_at || inv.statut_controle
			);
			setItems(compared);
		} catch {
			setError('Impossible de charger les rapports (vérifiez back_EMP_Fact sur le port 8001).');
		} finally {
			setLoading(false);
		}
	}, [user]);

	useEffect(() => {
		loadReports();
	}, [loadReports]);

	const tableRows = useMemo(
		() =>
			items.map((inv) => ({
				id: inv.id,
				facture: buildCompactDocParts(
					inv.numero_facture,
					inv.date_facture,
					inv.id,
					'FACT'
				),
				dum: buildCompactDocParts(
					inv.numero_declaration_dum,
					inv.date_declaration_dum,
					inv.dum_document_id,
					'DUM'
				),
				dumId: inv.dum_document_id,
				statutControle: inv.statut_controle,
				statutLabel: controleLabel(inv.statut_controle),
				pfnDum: inv.montant_declare_dum,
				netPay: inv.net_pay,
				ecart: inv.ecart_montant,
				devise: inv.devise_declaree_dum || inv.devise || '',
				comparedAt: formatHistoryDateTime(inv.compared_at),
			})),
		[items]
	);

	return (
		<div className="reports-page fade-up">
			<header className="reports-header">
				<div>
					<p className="reports-kicker">Traçabilité</p>
					<h1>Rapports de vérification</h1>
					<p className="reports-sub">
						Consultez chaque contrôle DUM ↔ facture et exportez un rapport PDF détaillé.
					</p>
				</div>
				<div className="reports-header-actions">
					<button type="button" className="reports-btn ghost" onClick={loadReports} disabled={loading}>
						<RefreshCw size={16} />
						Actualiser
					</button>
					<Link to="/cross-verification" className="reports-btn primary">
						<GitCompare size={16} />
						Nouveau contrôle
					</Link>
				</div>
			</header>

			{error ? (
				<section className="reports-card reports-error">
					<p>{error}</p>
				</section>
			) : null}

			<section className="reports-card">
				<div className="reports-table-head">
					<span>Facture</span>
					<span>DUM liée</span>
					<span>PFN / NET PAY</span>
					<span>Écart</span>
					<span>Statut</span>
					<span>Date</span>
					<span>Actions</span>
				</div>

				{loading ? (
					<p className="reports-empty">Chargement…</p>
				) : tableRows.length === 0 ? (
					<p className="reports-empty">
						Aucun contrôle enregistré. Lancez une{' '}
						<Link to="/cross-verification">vérification croisée</Link> puis comparez les totaux.
					</p>
				) : (
					tableRows.map((row) => (
						<div key={row.id} className="reports-table-row">
							<ReportsDocCell numero={row.facture.numero} date={row.facture.date} />
							<ReportsDocCell numero={row.dum.numero} date={row.dum.date} />
							<span className="reports-amounts">
								PFN {row.pfnDum ?? '—'} / NET {row.netPay ?? '—'} {row.devise}
							</span>
							<span>{row.ecart != null ? row.ecart : '—'}</span>
							<span>
								<span className={`reports-pill reports-pill--${row.statutControle || 'neutral'}`}>
									{row.statutLabel}
								</span>
							</span>
							<span>{row.comparedAt}</span>
							<span className="reports-actions">
								<Link to={`/reports/${row.id}`} className="reports-btn primary small">
									<Eye size={14} />
									Voir le rapport
								</Link>
							</span>
						</div>
					))
				)}
			</section>
		</div>
	);
}

export default ReportsPage;
