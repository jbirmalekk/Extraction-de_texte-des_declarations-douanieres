import { FileQuestion } from 'lucide-react';
import './ui.css';

function EmptyState({ title = 'Aucun élément', message, actions, icon: Icon = FileQuestion }) {
	return (
		<div className="emp-empty-state">
			<Icon size={40} color="#94a3b8" />
			<h3>{title}</h3>
			{message ? <p>{message}</p> : null}
			{actions ? <div className="emp-empty-state-actions">{actions}</div> : null}
		</div>
	);
}

export default EmptyState;
