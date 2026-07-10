import './ui.css';

function PageHeader({ kicker, title, subtitle, actions, className = '' }) {
	return (
		<header className={`emp-page-header ${className}`.trim()}>
			<div className="emp-page-header-copy">
				{kicker ? <p className="emp-page-kicker">{kicker}</p> : null}
				<h1>{title}</h1>
				{subtitle ? <p className="emp-page-sub">{subtitle}</p> : null}
			</div>
			{actions ? <div className="emp-page-header-actions">{actions}</div> : null}
		</header>
	);
}

export default PageHeader;
