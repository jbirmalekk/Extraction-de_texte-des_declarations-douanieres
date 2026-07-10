import { Link } from 'react-router-dom';
import './WorkflowBreadcrumb.css';

const WORKFLOWS = {
	dum: [
		{ key: 'import', label: 'Import', to: '/import' },
		{ key: 'ocr', label: 'Résultats OCR', to: '/ocr-result' },
		{ key: 'validation', label: 'Validation', to: '/validation' },
		{ key: 'cross', label: 'Réconciliation', to: '/cross-verification' },
		{ key: 'erp', label: 'Export ERP', to: '/erp-success' },
	],
	invoice: [
		{ key: 'import', label: 'Import', to: '/import' },
		{ key: 'ocr', label: 'Résultats OCR', to: '/invoice-ocr-result' },
		{ key: 'validation', label: 'Validation', to: '/invoice-validation' },
		{ key: 'cross', label: 'Réconciliation', to: '/cross-verification' },
		{ key: 'erp', label: 'Export ERP', to: '/erp-success' },
	],
};

function WorkflowBreadcrumb({ workflow = 'dum', current = 'validation', stepToOverrides = {} }) {
	const steps = WORKFLOWS[workflow] || WORKFLOWS.dum;
	const currentIndex = steps.findIndex((s) => s.key === current);

	return (
		<nav className="workflow-breadcrumb" aria-label="Étapes du parcours">
			<ol>
				{steps.map((step, index) => {
					const isCurrent = step.key === current;
					const isPast = currentIndex >= 0 && index < currentIndex;
					const targetTo = stepToOverrides[step.key] ?? step.to;
					const isNavigable = isPast || (isCurrent && step.key !== current);
					return (
						<li
							key={step.key}
							className={
								isCurrent ? 'is-current' : isPast ? 'is-past' : ''
							}
						>
							{isNavigable ? (
								<Link to={targetTo}>{step.label}</Link>
							) : (
								<span>{step.label}</span>
							)}
						</li>
					);
				})}
			</ol>
		</nav>
	);
}

export default WorkflowBreadcrumb;
