import { currentUser } from "@/lib/auth";
import type { ReactNode } from "react";

export default async function Home({ searchParams }: { searchParams?: Promise<{ error?: string }> }) {
  const user = await currentUser();
  const error = (await searchParams)?.error;

  return (
    <main className="marketing-shell">
      <header className="marketing-nav">
        <a className="marketing-brand" href="#top" aria-label="InboxPilot">
          <span className="marketing-logo" aria-hidden="true">
            <BotIcon />
          </span>
          <span>InboxPilot</span>
        </a>
        <nav aria-label="Navigation principale">
          <a href="#fonctionnalites">Fonctionnalités</a>
          <a href="#tarifs">Tarifs</a>
          <a href="#ressources">Ressources</a>
        </nav>
        <div className="marketing-nav-actions">
          {user ? (
            <a className="marketing-link" href="/dashboard">Mon espace</a>
          ) : (
            <a className="marketing-link" href="#connexion">Connexion</a>
          )}
          <a className="marketing-button primary" href={user ? "/dashboard" : "#inscription"}>
            Essayer gratuitement
          </a>
        </div>
      </header>

      <section id="top" className="marketing-hero">
        <div className="marketing-hero-copy">
          <p className="marketing-badge">Agent email IA</p>
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
            <a className="marketing-button primary large" href={user ? "/dashboard" : "#inscription"}>
              Démarrer gratuitement
            </a>
            <a className="marketing-button secondary large" href="#preview">
              <PlayIcon />
              Voir comment ça marche
            </a>
          </div>
          <div className="marketing-proof">
            <span>✓ Aucune carte requise</span>
            <span>✓ Essai gratuit 14 jours</span>
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
            <BotIcon />
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
          <span><GoogleLogo /> Google Workspace</span>
          <span><MailIcon /> IMAP</span>
        </div>
      </section>

      <section id="preview" className="dashboard-preview" aria-label="Aperçu du dashboard InboxPilot">
        <aside>
          <div className="preview-brand"><span><BotIcon /></span> InboxPilot</div>
          {["Vue d'ensemble", "Boîtes connectées", "Agents IA", "Brouillons", "Libellés & automatisations", "Activité", "Paramètres"].map((item, index) => (
            <div key={item} className={index === 0 ? "preview-menu active" : "preview-menu"}>
              {item}
            </div>
          ))}
          <div className="preview-plan">
            <strong>Plan Pro</strong>
            <span>1 000 emails / mois</span>
            <a href="#tarifs">Gérer mon abonnement →</a>
          </div>
        </aside>
        <div className="preview-main">
          <div className="preview-top">
            <strong>Vue d&apos;ensemble</strong>
            <a href={user ? "/settings" : "#inscription"}>Configurer l&apos;agent</a>
          </div>
          <div className="preview-hero">
            <div>
              <h2>Bonjour <span>Ilyesse</span></h2>
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
            <a href={user ? "/dashboard" : "#inscription"}>Voir toute l&apos;activité →</a>
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

      <section id="tarifs" className="pricing-section">
        <div className="section-title">
          <h2>Des tarifs simples et transparents</h2>
          <p>Choisissez l&apos;offre qui correspond à vos besoins.</p>
          <div className="billing-toggle">
            <span className="active">Mensuel</span>
            <span>Annuel</span>
            <em>-20%</em>
          </div>
        </div>
        <div className="pricing-grid">
          <PricingCard name="Free" price="0€" subtitle="Pour découvrir InboxPilot" cta="Commencer gratuitement" />
          <PricingCard name="Pro" price="19€" subtitle="Pour les professionnels" cta="Essayer 14 jours gratuitement" popular />
          <PricingCard name="Business" price="49€" subtitle="Pour les équipes" cta="Nous contacter" />
        </div>
        <p className="pricing-note">Essai gratuit 14 jours · Sans engagement · Annulez à tout moment</p>
      </section>

      {!user && (
        <section id="inscription" className="marketing-auth">
          <div>
            <p className="marketing-badge">Créer votre espace</p>
            <h2>Lancez InboxPilot en quelques minutes.</h2>
            <p>Créez votre compte, connectez Gmail ou Outlook, puis laissez l&apos;agent classer les nouveaux emails.</p>
          </div>
          <div className="marketing-forms">
            {error && <div className="error">Vérifie les informations saisies puis réessaie.</div>}
            <form action="/api/auth/register" method="post" className="marketing-form-card">
              <h3>Créer mon espace</h3>
              <label>Prénom et nom</label>
              <input name="ownerName" placeholder="Jean Martin" required />
              <label>Email professionnel</label>
              <input name="email" type="email" placeholder="jean@entreprise.fr" required />
              <label>Mot de passe</label>
              <input name="password" type="password" minLength={8} placeholder="Minimum 8 caractères" required />
              <button type="submit">Créer et continuer →</button>
            </form>
            <form id="connexion" action="/api/auth/login" method="post" className="marketing-form-card compact">
              <h3>Se connecter</h3>
              <label>Email</label>
              <input name="email" type="email" placeholder="jean@entreprise.fr" required />
              <label>Mot de passe</label>
              <input name="password" type="password" required />
              <button type="submit">Se connecter</button>
            </form>
          </div>
        </section>
      )}

      <footer id="ressources" className="marketing-footer">
        <div>
          <a className="marketing-brand" href="#top">
            <span className="marketing-logo" aria-hidden="true"><BotIcon /></span>
            <span>InboxPilot</span>
          </a>
          <p>Votre agent email IA pour classer, prioriser et garder le contrôle.</p>
        </div>
        <nav>
          <a href="#fonctionnalites">Fonctionnalités</a>
          <a href="#tarifs">Tarifs</a>
          <a href={user ? "/dashboard" : "#connexion"}>Connexion</a>
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

function PricingCard({ name, price, subtitle, cta, popular = false }: { name: string; price: string; subtitle: string; cta: string; popular?: boolean }) {
  const features = name === "Free"
    ? ["1 boîte connectée", "200 emails / mois", "Classement intelligent", "Brouillons manuels"]
    : name === "Pro"
      ? ["5 boîtes connectées", "5 000 emails / mois", "Actions automatiques", "Brouillons & réponses auto", "Support prioritaire"]
      : ["Boîtes illimitées", "Emails illimités", "Règles avancées & IA", "Statistiques avancées", "Support dédié"];

  return (
    <article className={popular ? "popular" : ""}>
      {popular && <em>Le plus populaire</em>}
      <h3>{name}</h3>
      <p>{subtitle}</p>
      <div><strong>{price}</strong><span>/ mois</span></div>
      <ul>
        {features.map((feature) => <li key={feature}>✓ {feature}</li>)}
      </ul>
      <a href="#inscription">{cta}</a>
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

function BotIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true">
      <rect x="8" y="14" width="32" height="24" rx="10" fill="currentColor" opacity=".18" />
      <path d="M17 27c0-4 3-7 7-7s7 3 7 7" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <circle cx="18" cy="28" r="2" fill="currentColor" />
      <circle cx="30" cy="28" r="2" fill="currentColor" />
      <path d="M24 14V8" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <circle cx="24" cy="7" r="3" fill="currentColor" />
      <path d="M16 35h16" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
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
