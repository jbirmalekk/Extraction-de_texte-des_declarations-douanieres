import { WORKFLOW_STEPS } from '@/shared/utils/workflowProgress';
import './ui.css';

function WorkflowTimeline({ steps, title = 'Parcours document', compact = false }) {
	const resolved =
		steps ||
		WORKFLOW_STEPS.map((s) => ({ ...s, state: 'pending' }));

	return (
		<div className={`emp-workflow-timeline${compact ? ' emp-workflow-timeline--compact' : ''}`}>
			{title ? <p className="emp-workflow-timeline-title">{title}</p> : null}
			<ol className="emp-workflow-steps" aria-label={title || 'Parcours'}>
				{resolved.map((step) => (
					<li
						key={step.key}
						className={`emp-workflow-step${step.state === 'done' ? ' is-done' : ''}${step.state === 'current' ? ' is-current' : ''}`}
					>
						<span className="emp-workflow-step-dot" aria-hidden="true">
							{step.state === 'done' ? '✓' : step.state === 'current' ? '●' : ''}
						</span>
						<span className="emp-workflow-step-label">
							{compact ? step.short || step.label : step.label}
						</span>
					</li>
				))}
			</ol>
		</div>
	);
}

export default WorkflowTimeline;
