import { Link } from 'react-router-dom';

function WelcomePage() {
	return (
		<div className="welcome-container">
			<main className="welcome-main">
				<section className="hero-content">
					<h1 className="hero-title">
						All your customs documents,
						<span className="gradient-text"> in one click</span>
					</h1>
					<p className="hero-description">
						Your competitive advantage is here. Automatically process and validate customs declarations,
						invoices, and documents for your growing business in minutes. Free to send and download.
					</p>

					<div className="hero-cta">
						<Link to="/register" className="btn-primary">
							Create Account
							<svg className="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
								<path d="M5 12h14M12 5l7 7-7 7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
							</svg>
						</Link>
					</div>
				</section>
				<div className="hero-preview">
					<div className="doc-card">
						<div className="doc-header">
							<div className="doc-icon">📄</div>
							<div>
								<p className="doc-type-label">Document Type</p>
								<p className="doc-type">Customs Declaration</p>
							</div>
						</div>
						<div className="doc-body">
							<p className="doc-body-title">Declaration Details</p>
							<div className="doc-lines">
								<span />
								<span />
								<span />
								<span className="short" />
							</div>
						</div>
						<div className="doc-footer">
							<span className="pulse" /> Processing…
						</div>
					</div>
				</div>
			</main>
		</div>
	);
}

export default WelcomePage;
