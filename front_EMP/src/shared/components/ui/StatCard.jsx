import { Link } from 'react-router-dom';
import './ui.css';

function StatCard({ label, value, hint, icon: Icon, color = '#2563eb', to, loading = false }) {
	const content = (
		<>
			<div className="emp-stat-icon" style={{ color, backgroundColor: `${color}18` }}>
				{Icon ? <Icon size={20} /> : null}
			</div>
			<div>
				<p className="emp-stat-label">{label}</p>
				<p className="emp-stat-value">{loading ? '…' : value}</p>
				{hint ? <p className="emp-stat-hint">{hint}</p> : null}
			</div>
		</>
	);

	if (to) {
		return (
			<Link to={to} className="emp-stat-card emp-stat-card--clickable">
				{content}
			</Link>
		);
	}

	return <article className="emp-stat-card">{content}</article>;
}

export default StatCard;
