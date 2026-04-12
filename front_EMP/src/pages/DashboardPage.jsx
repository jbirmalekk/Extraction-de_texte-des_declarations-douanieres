import { ArrowRight, CheckCircle, Clock, Database, FileText, FileUp } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const stats = [
  { label: 'Documents processed', value: 142, icon: FileText, color: '#2563eb' },
  { label: 'Validated this month', value: 38, icon: CheckCircle, color: '#16a34a' },
  { label: 'Pending validation', value: 7, icon: Clock, color: '#f59e0b' },
  { label: 'Integrated to ERP', value: 127, icon: Database, color: '#8b5cf6' },
];

const activities = [
  { doc: 'INV-2024-0542', date: '2026-03-18', status: 'Validated', tone: 'success' },
  { doc: 'INV-2024-0541', date: '2026-03-17', status: 'Pending', tone: 'warning' },
  { doc: 'INV-2024-0540', date: '2026-03-17', status: 'Integrated', tone: 'info' },
  { doc: 'INV-2024-0539', date: '2026-03-16', status: 'Validated', tone: 'success' },
  { doc: 'INV-2024-0538', date: '2026-03-16', status: 'Pending', tone: 'warning' },
];

function DashboardPage() {
  const { user } = useAuth();

  return (
    <>
      <section className="dashboard-hero modern">
        <div>
          <p className="hero-pill">Pilotage OCR</p>
          <h1>Tableau de bord</h1>
          <p className="subtitle">Visualisez la performance de vos imports et accedez vite aux actions prioritaires.</p>
        </div>
        <Link to="/import" className="hero-import-btn">
          <FileUp size={18} />
          Nouveau document
        </Link>
      </section>

      <section className="stats-grid">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="stat-card">
            <div className="stat-icon" style={{ color, backgroundColor: `${color}15` }}>
              <Icon size={20} />
            </div>
            <div>
              <p className="stat-label">{label}</p>
              <p className="stat-value">{value}</p>
            </div>
          </div>
        ))}
      </section>

    

      <section className="activities">
        <div className="section-header">
          <h2>Recent activity</h2>
          {user?.role === 'admin' ? (
            <Link to="/history" className="text-link">See all</Link>
          ) : (
            <Link to="/import" className="text-link">Upload more</Link>
          )}
        </div>
        <div className="activity-table">
          <div className="table-head">
            <span>Document</span>
            <span>Date</span>
            <span>Status</span>
            <span>Action</span>
          </div>
          {activities.map(({ doc, date, status, tone }) => (
            <div key={doc} className="table-row">
              <span>{doc}</span>
              <span>{date}</span>
              <span><span className={`status-pill ${tone}`}>{status}</span></span>
              <span>
                <button className="table-action">
                  Voir <ArrowRight size={14} />
                </button>
              </span>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

export default DashboardPage;
