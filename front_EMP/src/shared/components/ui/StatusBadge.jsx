import './ui.css';

const TONE_MAP = {
	ok: 'ok',
	success: 'success',
	warning: 'warning',
	warn: 'warning',
	error: 'error',
	info: 'info',
	neutral: 'neutral',
};

function StatusBadge({ label, tone = 'neutral' }) {
	const t = TONE_MAP[tone] || tone || 'neutral';
	return <span className={`emp-status-badge emp-status-badge--${t}`}>{label}</span>;
}

export default StatusBadge;
