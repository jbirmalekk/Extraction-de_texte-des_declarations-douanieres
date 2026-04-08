function HistoryPage() {
  return (
    <div className="history-page">
      <section className="dashboard-hero modern">
        <div>
          <p className="hero-pill">Traçabilite</p>
          <h1>Historique des traitements</h1>
          <p className="subtitle">Suivez ici les imports, validations et statuts d&apos;integration.</p>
        </div>
      </section>

      <section className="activities history-empty">
        <h2>Historique bientot disponible</h2>
        <p>La connexion aux donnees sera branchee dans la prochaine etape.</p>
      </section>
    </div>
  );
}

export default HistoryPage;
