import { currentUser } from "@/lib/auth";
import { PricingSection } from "./PricingSection";
import type { ReactNode } from "react";

export default async function Home() {
  const user = await currentUser();
  const connectionHref = user ? "/dashboard" : "/connexion";

  return (
    <main className="marketing-shell">
      <header className="marketing-nav">
        <a className="marketing-brand" href="#top" aria-label="InboxPilot">
          <span className="marketing-logo" aria-hidden="true">
            <InboxPilotLogo />
          </span>
          <span>InboxPilot</span>
        </a>
        <nav aria-label="Navigation principale">
          <a href="#top">Fonctionnalités</a>
          <a href="#preview">Fonctionnement</a>
          <a href="#tarifs">Tarifs</a>
        </nav>
        <div className="marketing-nav-actions">
          <a className="marketing-link" href={connectionHref}>Connexion</a>
          <a className="marketing-button primary" href="#tarifs">
            Voir les offres
          </a>
        </div>
      </header>

      <section id="top" className="marketing-hero">
        <div className="marketing-hero-copy">
          <h1>
            Votre boîte mail.
            <br />
            Triée. Classée.
            <br />
            <span>Sous contrôle.</span>
          </h1>
          <p>
            InboxPilot est un agent IA qui analyse, classe et traite automatiquement vos emails
            pour ne garder que l&apos;essentiel. Gagnez du temps chaque jour.
          </p>
          <div className="marketing-hero-actions">
            <a className="marketing-button primary large" href="#tarifs">
              Démarrer mon abonnement
            </a>
          </div>
        </div>

        <div className="marketing-hero-visual" aria-hidden="true">
          <div className="orbit-rings" />
          <div className="floating-card gmail-card">
            <GmailLogo />
          </div>
          <div className="floating-card outlook-card">
            <OutlookLogo />
          </div>
          <div className="bot-card">
            <InboxPilotLogo />
          </div>
          <div className="analysis-toast">
            <span />
            <strong>Analyse en cours...</strong>
            <small>Classement intelligent des emails</small>
          </div>
        </div>
      </section>

      <section className="tool-strip" aria-label="Connecteurs">
        <p>Connecté avec vos outils préférés</p>
        <div>
          <span><GmailLogo /> Gmail</span>
          <span><OutlookLogo /> Outlook</span>
          <span><MicrosoftLogo /> Microsoft 365</span>
        </div>
      </section>

      <section id="preview" className="dashboard-preview compact-preview" aria-label="Aperçu du dashboard InboxPilot">
        <div className="preview-main">
          <div className="preview-top">
            <strong>Vue d&apos;ensemble</strong>
            <a href="#tarifs">Configurer l&apos;agent</a>
          </div>
          <div className="preview-hero">
            <div>
              <h2>Bonjour</h2>
              <p>
                InboxPilot a classé 3 emails cette semaine et vous aide à garder votre boîte
                de réception sous contrôle.
              </p>
              <button>Voir l&apos;activité récente →</button>
            </div>
            <div className="preview-stats">
              <article><strong>2</strong><span>Boîtes connectées</span><small>+12%</small></article>
              <article><strong>3</strong><span>Emails classés / 7 jours</span><small>+18%</small></article>
              <article><strong>0</strong><span>Brouillons préparés</span></article>
              <article><strong>0</strong><span>Suppressions auto</span></article>
            </div>
          </div>
          <div className="preview-activity">
            <h3>Activité récente</h3>
            <PreviewEmail icon={<OutlookLogo />} title="Bienvenue dans votre nouveau compte Outlook.com" label="FYI" />
            <PreviewEmail icon={<GmailLogo />} title="Votre code à usage unique" label="Notification" />
            <PreviewEmail icon={<GmailLogo />} title="RECRUTEMENT" label="FYI" />
            <a href="#tarifs">Voir toute l&apos;activité →</a>
          </div>
        </div>
      </section>

      <section id="fonctionnalites" className="feature-section">
        <h2>Pourquoi choisir InboxPilot ?</h2>
        <div className="feature-cards">
          <FeatureCard icon={<SparkIcon />} title="Tri intelligent par IA">
            L&apos;agent comprend vos emails et les classe automatiquement selon leur contenu.
          </FeatureCard>
          <FeatureCard icon={<BoltIcon />} title="Actions automatiques">
            Prépare des brouillons, répond automatiquement ou supprime selon vos règles.
          </FeatureCard>
          <FeatureCard icon={<LockIcon />} title="Contrôle total">
            Vous gardez le contrôle sur toutes les actions et pouvez modifier à tout moment.
          </FeatureCard>
          <FeatureCard icon={<ShieldIcon />} title="Sécurisé & privé">
            Vos données restent privées et sont traitées avec les plus hauts standards.
          </FeatureCard>
        </div>
      </section>

      <PricingSection />

      <footer id="ressources" className="marketing-footer">
        <div>
          <a className="marketing-brand" href="#top">
            <span className="marketing-logo" aria-hidden="true"><InboxPilotLogo /></span>
            <span>InboxPilot</span>
          </a>
          <p>Votre agent email IA pour classer, prioriser et garder le contrôle.</p>
        </div>
        <nav>
          <a href="#top">Fonctionnalités</a>
          <a href="#preview">Fonctionnement</a>
          <a href="#tarifs">Tarifs</a>
          <a href={connectionHref}>Connexion</a>
        </nav>
        <small>© 2026 InboxPilot. Tous droits réservés.</small>
      </footer>
    </main>
  );
}

function FeatureCard({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <article>
      <span>{icon}</span>
      <h3>{title}</h3>
      <p>{children}</p>
    </article>
  );
}

function PreviewEmail({ icon, title, label }: { icon: ReactNode; title: string; label: string }) {
  return (
    <div className="preview-email">
      <span>{icon}</span>
      <div>
        <strong>{title}</strong>
        <small>no-reply@example.com</small>
      </div>
      <em>{label}</em>
    </div>
  );
}

function InboxPilotLogo() {
  return (
    <svg className="inboxpilot-logo-mark" viewBox="0 0 96 96" aria-hidden="true">
      <rect x="8" y="8" width="80" height="80" rx="22" fill="#fff" />
      <rect x="25" y="24" width="13" height="13" rx="2" fill="#2563ff" />
      <rect x="43" y="24" width="13" height="13" rx="2" fill="#2563ff" />
      <rect x="25" y="43" width="13" height="31" rx="2" fill="#111827" />
      <path
        d="M43 43h17.5C72.5 43 81 35.7 81 25.6C81 15.8 73.2 9 61.1 9H43v65h13V54h4.4C74.2 54 88 43.6 88 26.2C88 8.9 75.4 0 60.3 0H43v12h16.5C69.8 12 76 17.7 76 26.4C76 35.1 69.6 43 59.4 43H43Z"
        fill="#2563ff"
      />
    </svg>
  );
}

function GmailLogo() {
  return (
    <svg viewBox="0 0 64 48" aria-hidden="true">
      <path d="M7 8h50v32a5 5 0 0 1-5 5H12a5 5 0 0 1-5-5V8Z" fill="#fff" />
      <path d="M7 13.3V40a5 5 0 0 0 5 5h8V23.5L7 13.3Z" fill="#4285F4" />
      <path d="M44 45h8a5 5 0 0 0 5-5V13.3L44 23.5V45Z" fill="#34A853" />
      <path d="M7 10.5c0-3.3 3.8-5.1 6.3-3.1L32 21.7 50.7 7.4c2.5-2 6.3-.2 6.3 3.1v2.8L32 32.5 7 13.3v-2.8Z" fill="#EA4335" />
      <path d="M44 23.5 57 13.3V10.5c0-3.3-3.8-5.1-6.3-3.1L44 12.5v11Z" fill="#FBBC04" />
    </svg>
  );
}

function OutlookLogo() {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true">
      <path d="M24 13h28a4 4 0 0 1 4 4v30a4 4 0 0 1-4 4H24V13Z" fill="#28A8EA" />
      <path d="M24 17h28v9H24v-9Z" fill="#50D9FF" opacity=".75" />
      <path d="M24 27h32v20L40 36 24 47V27Z" fill="#0078D4" />
      <rect x="8" y="20" width="28" height="28" rx="4" fill="#0A6CFF" />
      <path d="M22 40c-5 0-8-3.7-8-8s3-8 8-8 8 3.7 8 8-3 8-8 8Zm0-4c2.4 0 3.8-1.8 3.8-4S24.4 28 22 28s-3.8 1.8-3.8 4 1.4 4 3.8 4Z" fill="#fff" />
    </svg>
  );
}

function MicrosoftLogo() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#f35325" d="M4 4h19v19H4z" />
      <path fill="#81bc06" d="M25 4h19v19H25z" />
      <path fill="#05a6f0" d="M4 25h19v19H4z" />
      <path fill="#ffba08" d="M25 25h19v19H25z" />
    </svg>
  );
}

function GoogleLogo() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 7.9 3l5.7-5.7C34 6 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5Z" />
      <path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15 19 12 24 12c3 0 5.8 1.1 7.9 3l5.7-5.7C34 6 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7Z" />
      <path fill="#4CAF50" d="M24 44c5.1 0 9.8-1.9 13.3-5.1l-6.1-5.2C29.2 35.2 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44Z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.1-4.1 5.7l6.1 5.2C36.9 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5Z" />
    </svg>
  );
}

function MailIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true">
      <rect x="7" y="12" width="34" height="24" rx="5" fill="none" stroke="currentColor" strokeWidth="3" />
      <path d="m9 15 15 13 15-13" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M9 7.5v9l7-4.5-7-4.5Z" fill="currentColor" />
    </svg>
  );
}

function SparkIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2 9.8 8.5 3 11l6.8 2.5L12 20l2.2-6.5L21 11l-6.8-2.5L12 2Z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" /></svg>
  );
}

function BoltIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 2 4 14h7l-1 8 10-13h-7l1-7Z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" /></svg>
  );
}

function LockIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10V8a5 5 0 0 1 10 0v2M6 10h12v10H6V10Z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" /></svg>
  );
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 5 6v5c0 5 3 8.5 7 10 4-1.5 7-5 7-10V6l-7-3Z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" /></svg>
  );
}
