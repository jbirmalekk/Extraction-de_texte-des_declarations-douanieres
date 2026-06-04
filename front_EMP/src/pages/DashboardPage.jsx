import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, CheckCircle, Clock, Database, FileText, FileUp } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { fetchUnifiedHistoryBatch } from '../services/historyService';
import { fetchMyDashboard } from '../services/ocrService';

const DEFAULT_STATS = [
  { key: 'documents_processed', label: 'Documents traités', icon: FileText, color: '#2563eb' },
  { key: 'validated_this_month', label: 'Validés ce mois', icon: CheckCircle, color: '#16a34a' },
  { key: 'pending_validation', label: 'En attente de validation', icon: Clock, color: '#f59e0b' },
  { key: 'ready_for_erp', label: 'Prêts ERP', icon: Database, color: '#8b5cf6' },
];

function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState({ stats: {}, recent_activity: [] });
  const [recentUnified, setRecentUnified] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const monthlyIndicators = dashboard?.monthly_indicators || [];

  useEffect(() => {
    if (user?.role === 'admin') {
      navigate('/admin/dashboard', { replace: true });
    }
  }, [navigate, user?.role]);

  useEffect(() => {
    let isActive = true;

    const loadDashboard = async () => {
      setLoading(true);
      setError('');

      try {
        const data = await fetchMyDashboard();
        if (isActive) {
          setDashboard(data || { stats: {}, recent_activity: [] });
        }
      } catch (_fetchError) {
        if (isActive) {
          setError('Impossible de charger votre tableau de bord pour le moment.');
        }
      }

      try {
        const unified = await fetchUnifiedHistoryBatch({
          isAdmin: false,
          user,
          limit: 5,
        });
        if (isActive) {
          setRecentUnified((unified?.rows || []).slice(0, 5));
        }
      } catch {
        if (isActive) {
          setRecentUnified([]);
        }
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    };

    loadDashboard();

    return () => {
      isActive = false;
    };
  }, [user]);

  const stats = useMemo(
    () =>
      DEFAULT_STATS.map((item) => ({
        ...item,
        value: dashboard?.stats?.[item.key] ?? 0,
      })),
    [dashboard],
  );

  const activities = dashboard?.recent_activity || [];
  const recentRows =
    recentUnified.length > 0
      ? recentUnified
      : activities.map((a) => ({
          id: `dum-${a.document_id}`,
          type: 'dum',
          typeLabel: 'DUM',
          reference: a.document,
          dateLabel: a.date,
          status: a.status,
          statusTone: a.tone,
          dumId: a.document_id,
          invoiceId: null,
        }));
  const monthlyPeak = useMemo(
    () => Math.max(1, ...monthlyIndicators.map((item) => Number(item.documents_processed || 0))),
    [monthlyIndicators],
  );

  return (
    <>
      <section className="dashboard-hero modern">
        <div>
          <p className="hero-pill">Pilotage OCR</p>
          <h1>Tableau de bord</h1>
        <p className="subtitle">
        {user?.username
          ? `Bonjour ${user.username}, voici la synthèse de vos imports et validations.`
          : 'Visualisez la performance de vos imports et accedez vite aux actions prioritaires.'}
        </p>
        </div>
        <Link to="/import" className="hero-import-btn">
          <FileUp size={18} />
          Nouveau document
        </Link>
      </section>

      {error ? (
      <section className="activities history-empty">
        <p>{error}</p>
      </section>
      ) : null}

      <section className="stats-grid">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="stat-card">
            <div className="stat-icon" style={{ color, backgroundColor: `${color}15` }}>
              <Icon size={20} />
            </div>
            <div>
              <p className="stat-label">{label}</p>
          <p className="stat-value">{loading ? '…' : value}</p>
            </div>
          </div>
        ))}
      </section>

        <section className="activities">
          <div className="section-header">
            <h2>Indicateurs mensuels</h2>
          </div>
          <div className="month-mini-grid">
            {monthlyIndicators.map((item) => (
              <article key={item.month} className="month-mini-card">
                <div className="month-mini-card-head">
                  <div>
                    <p className="month-mini-label">{item.label}</p>
                    <h3>{item.month}</h3>
                  </div>
                  <span className="month-mini-chip">{item.documents_processed} docs</span>
                </div>
                <div className="month-mini-track" aria-hidden="true">
                  <span
                    className="month-mini-fill"
                    style={{ width: `${(Number(item.documents_processed || 0) / monthlyPeak) * 100}%` }}
                  />
                </div>
                <div className="month-mini-values">
                  <div>
                    <strong>{item.documents_processed}</strong>
                    <small>documents traités</small>
                  </div>
                  <div>
                    <strong>{item.validated}</strong>
                    <small>validés</small>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

      <section className="activities">
        <div className="section-header">
          <h2>Activité récente</h2>
          <Link to="/history" className="text-link">Tout voir</Link>
        </div>
        <div className="activity-table">
          <div className="table-head">
            <span>Type</span>
            <span>Document</span>
            <span>Date</span>
            <span>Statut</span>
            <span>Action</span>
          </div>
          {loading ? (
          <div className="table-row">
            <span>—</span>
            <span>Chargement...</span>
            <span>—</span>
            <span><span className="status-pill warning">En cours</span></span>
            <span>
            <button className="table-action" type="button" disabled>
              Voir <ArrowRight size={14} />
            </button>
            </span>
          </div>
          ) : recentRows.length > 0 ? (
            recentRows.map((row) => (
            <div key={row.id} className="table-row">
            <span>{row.typeLabel || 'DUM'}</span>
            <span>{row.reference}</span>
            <span>{row.dateLabel || row.date}</span>
            <span><span className={`status-pill ${row.statusTone || row.tone}`}>{row.status}</span></span>
            <span>
                <Link
                  className="table-action"
                  to={row.type === 'invoice' ? `/invoices/${row.invoiceId}` : `/documents/${row.dumId}`}
                >
                  Voir <ArrowRight size={14} />
                </Link>
            </span>
            </div>
          ))
          ) : (
          <div className="table-row">
            <span>Aucun document</span>
            <span>—</span>
            <span><span className="status-pill info">Vide</span></span>
              <span>
              <button className="table-action" type="button" disabled>
                Voir <ArrowRight size={14} />
              </button>
              </span>
          </div>
          )}
        </div>
      </section>
    </>
  );
}

export default DashboardPage;
