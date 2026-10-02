import type { ReactNode } from "react";

export const LEGAL_VERSION = "2026-10-02";

export const COMPANY = {
  name: "SPIDR",
  legalForm: "Société par actions simplifiée unipersonnelle au capital de 1 000 euros",
  registration: "RCS Pontoise B 841 816 903",
  vat: "FR43841816903",
  address: "60 rue de l’Aveyron, 95100 Argenteuil, France",
  representative: "Geoffroy Detrousselle",
};

export default function LegalPage({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <main className="legal-shell">
      <header className="legal-header">
        <a className="legal-brand" href="/">InboxPilot</a>
        <nav aria-label="Navigation juridique">
          <a href="/legal/cgv">CGV</a>
          <a href="/legal/cgu">CGU</a>
          <a href="/legal/privacy">Confidentialité</a>
        </nav>
        <a className="legal-back" href="/connexion">Connexion</a>
      </header>

      <article className="legal-document">
        <div className="legal-title">
          <span>Informations contractuelles</span>
          <h1>{title}</h1>
          <p>{description}</p>
          <small>Version du 2 octobre 2026</small>
        </div>
        <div className="legal-content">{children}</div>
      </article>

      <footer className="legal-footer">
        <span>© 2026 InboxPilot - {COMPANY.name}</span>
        <nav>
          <a href="/legal/cgv">CGV</a>
          <a href="/legal/cgu">CGU</a>
          <a href="/legal/privacy">Politique de confidentialité</a>
        </nav>
      </footer>
    </main>
  );
}

export function CompanyIdentity() {
  return (
    <p>
      Le service InboxPilot est édité par <strong>{COMPANY.name}</strong>, {COMPANY.legalForm}, immatriculée au {COMPANY.registration},
      TVA intracommunautaire {COMPANY.vat}, dont le siège social est situé {COMPANY.address}, représentée par {COMPANY.representative}.
    </p>
  );
}
