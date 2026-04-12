import { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

function WelcomePage() {
	const location = useLocation();

	useEffect(() => {
		if (!location.hash) {
			return;
		}

		const targetId = location.hash.replace('#', '');
		const targetElement = document.getElementById(targetId);

		if (targetElement) {
			window.requestAnimationFrame(() => {
				targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
			});
		}
	}, [location.hash]);

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

			<section id="details" className="welcome-secondary details-section">
				<div className="welcome-section-head">
					<p className="welcome-kicker">Detail</p>
					<h2>Pourquoi EMP SmartOCR</h2>
				</div>
				<div className="details-grid">
					<article className="detail-card">
						<h3>Extraction rapide</h3>
						<p>Capture automatique des donnees clefs depuis vos documents en quelques secondes.</p>
					</article>
					<article className="detail-card">
						<h3>Validation intelligente</h3>
						<p>Controle de coherence pour limiter les erreurs manuelles avant integration.</p>
					</article>
					<article className="detail-card">
						<h3>Suivi centralise</h3>
						<p>Historique clair des imports et du statut de traitement de chaque document.</p>
					</article>
				</div>
			</section>

			<section id="contact" className="welcome-secondary contact-section">
				<div className="welcome-section-head">
					<p className="welcome-kicker">Contact</p>
					<h2>Besoin d&apos;aide ou d&apos;une demo</h2>
				</div>
				<div className="contact-card">
					<p>Notre equipe peut vous aider a configurer votre flux OCR selon vos besoins metier.</p>
					<a href="mailto:contact@emp-ocr.com" className="contact-link">contact@emp-ocr.com</a>
				</div>
			</section>
		</div>
	);
}

export default WelcomePage;
