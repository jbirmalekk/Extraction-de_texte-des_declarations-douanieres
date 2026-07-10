import DocTypeBadge from './DocTypeBadge';
import WorkflowTimeline from './WorkflowTimeline';
import './ui.css';

function ValidationContextStrip({
	type = 'dum',
	reference,
	fileName,
	fieldsToCorrect = 0,
	totalFields = 0,
	workflowSteps,
}) {
	return (
		<div className="emp-validation-context">
			<div className="emp-validation-context-head">
				<DocTypeBadge type={type} />
				<div>
					<strong>{reference || '—'}</strong>
					{fileName ? <p className="emp-validation-context-file">{fileName}</p> : null}
				</div>
				{totalFields > 0 ? (
					<span className="emp-validation-context-stats">
						{fieldsToCorrect > 0 ? (
							<>
								<strong className="is-warn">{fieldsToCorrect}</strong> champ
								{fieldsToCorrect > 1 ? 's' : ''} à corriger
							</>
						) : (
							<span className="emp-validation-context-ok">Aucune correction requise</span>
						)}
						<small> / {totalFields} champs</small>
					</span>
				) : null}
			</div>
			{workflowSteps ? (
				<WorkflowTimeline compact title="Parcours" steps={workflowSteps} />
			) : null}
		</div>
	);
}

export default ValidationContextStrip;
