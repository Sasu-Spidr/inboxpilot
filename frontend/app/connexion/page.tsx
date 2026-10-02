import { redirect } from "next/navigation";

import { signupAccessCodeRequired } from "@/lib/antiAbuse";
import { currentUser } from "@/lib/auth";
import { publicSignupEnabled, signupEmailAllowed } from "@/lib/features";

import AuthError from "../AuthError";

export default async function ConnexionPage({
  searchParams,
}: {
  searchParams?: Promise<{ error?: string; signup?: string; login?: string }>;
}) {
  if (await currentUser()) redirect("/dashboard");

  const params = await searchParams;
  const error = params?.error;
  const invitedEmail = String(params?.signup || "").trim().toLowerCase();
  const loginEmail = String(params?.login || "").trim().toLowerCase();
  const invitedSignup = signupEmailAllowed(invitedEmail);
  const signupEnabled = publicSignupEnabled() || invitedSignup;
  const accessCodeRequired = signupAccessCodeRequired();
  const turnstileSiteKey = process.env.TURNSTILE_SITE_KEY || "";

  return (
    <main className="auth-shell">
      <section className="hero-card" aria-label="Présentation InboxPilot">
        <div className="brand-pill">
          <span className="brand-icon" aria-hidden="true">
            <InboxPilotLogo />
          </span>
          <span>InboxPilot</span>
        </div>

        <div className="hero-copy">
          <p className="eyebrow">Agent email autonome</p>
          <h1>
            Connectez vos boîtes. <span>L&apos;agent trie le reste.</span>
          </h1>
          <p>
            Gmail et Outlook connectés proprement : emails classés, libellés appliqués,
            brouillons prêts à relire. Les actions suivent vos paramètres.
          </p>
        </div>

        <div className="feature-grid" aria-label="Fonctionnalités principales">
          <span>Gmail OAuth</span>
          <span>Hotmail / Outlook</span>
          <span>Brouillons IA</span>
          <span>Labels automatiques</span>
        </div>
      </section>

      <section className="auth-panel">
        <AuthError code={error} email={loginEmail || invitedEmail} />
        <div className="forms">
          {signupEnabled ? (
            <form action="/api/auth/register" method="post" className="form-card">
              <h2>Créer mon espace</h2>
              <input type="hidden" name="signupStartedAt" value={Date.now()} />
              <label className="bot-field" aria-hidden="true">
                Site web
                <input name="companyWebsite" tabIndex={-1} autoComplete="off" />
              </label>
              <label>Prénom et nom</label>
              <input name="ownerName" placeholder="Jean Martin" required />
              <label>Email professionnel</label>
              <input
                name="email"
                type="email"
                placeholder="jean@entreprise.fr"
                defaultValue={invitedSignup ? invitedEmail : ""}
                readOnly={invitedSignup}
                required
              />
              <label>Mot de passe</label>
              <input name="password" type="password" minLength={8} placeholder="Minimum 8 caractères" required />
              {accessCodeRequired && (
                <>
                  <label>Code d&apos;accès</label>
                  <input name="signupAccessCode" placeholder="Code communiqué par InboxPilot" required />
                </>
              )}
              {turnstileSiteKey && <div className="cf-turnstile" data-sitekey={turnstileSiteKey} />}
              <input type="hidden" name="legalVersion" value="2026-10-02" />
              <label className="legal-consent">
                <input name="legalAccepted" type="checkbox" required />
                <span>
                  J’accepte les <a href="/legal/cgu" target="_blank" rel="noreferrer">CGU</a> et les <a href="/legal/cgv" target="_blank" rel="noreferrer">CGV</a>,
                  et j’ai lu la <a href="/legal/privacy" target="_blank" rel="noreferrer">politique de confidentialité</a>.
                </span>
              </label>
              <button type="submit">Créer et continuer →</button>
              <p className="form-switch">
                Déjà inscrit ? <a href="#connexion">Se connecter</a>
              </p>
            </form>
          ) : (
            <article className="form-card">
              <h2>Accès sur invitation</h2>
              <p>
                Les nouvelles inscriptions sont momentanément validées manuellement afin de protéger la plateforme.
                Si vous avez déjà un compte, connectez-vous avec vos identifiants.
              </p>
            </article>
          )}

          <form id="connexion" action="/api/auth/login" method="post" className="form-card secondary">
            <h2>Se connecter</h2>
            <label>Email</label>
            <input
              name="email"
              type="email"
              placeholder="jean@entreprise.fr"
              defaultValue={loginEmail}
              required
            />
            <label>Mot de passe</label>
            <input name="password" type="password" required />
            <button type="submit">Se connecter</button>
          </form>
        </div>
        <nav className="auth-legal-links" aria-label="Informations juridiques">
          <a href="/legal/cgv">CGV</a>
          <a href="/legal/cgu">CGU</a>
          <a href="/legal/privacy">Confidentialité</a>
        </nav>
      </section>
    </main>
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
