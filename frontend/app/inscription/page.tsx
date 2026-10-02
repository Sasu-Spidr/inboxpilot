import { redirect } from "next/navigation";

import { signupAccessCodeRequired } from "@/lib/antiAbuse";
import { currentUser } from "@/lib/auth";
import { signupEmailAllowed } from "@/lib/features";

import AuthError from "../AuthError";

export default async function InscriptionPage({
  searchParams,
}: {
  searchParams?: Promise<{ email?: string; error?: string }>;
}) {
  if (await currentUser()) redirect("/dashboard");

  const params = await searchParams;
  const email = String(params?.email || "").trim().toLowerCase();
  if (!signupEmailAllowed(email)) redirect("/connexion");

  const accessCodeRequired = signupAccessCodeRequired();
  const turnstileSiteKey = process.env.TURNSTILE_SITE_KEY || "";

  return (
    <main className="auth-shell">
      <section className="hero-card" aria-label="Présentation InboxPilot">
        <div className="brand-pill">InboxPilot</div>
        <div className="hero-copy">
          <p className="eyebrow">Compte de test autorisé</p>
          <h1>
            Créez votre espace. <span>Connectez ensuite Gmail.</span>
          </h1>
          <p>
            Cette invitation est réservée à l’adresse de test autorisée pour valider le parcours InboxPilot en dev.
          </p>
        </div>
      </section>

      <section className="auth-panel">
        <AuthError code={params?.error} email={email} />
        <div className="forms">
          <form action="/api/auth/register" method="post" className="form-card">
            <h2>Créer mon espace</h2>
            <input type="hidden" name="signupStartedAt" value={Date.now()} />
            <label className="bot-field" aria-hidden="true">
              Site web
              <input name="companyWebsite" tabIndex={-1} autoComplete="off" />
            </label>
            <label>Prénom et nom</label>
            <input name="ownerName" placeholder="Compte de test InboxPilot" required />
            <label>Email</label>
            <input name="email" type="email" value={email} readOnly required />
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
          </form>
        </div>
        <nav className="auth-legal-links" aria-label="Informations juridiques">
          <a href="/legal/cgv">CGV</a>
          <a href="/legal/cgu">CGU</a>
          <a href="/legal/privacy">Confidentialité</a>
          <a href="/legal/mentions">Mentions légales</a>
        </nav>
      </section>
    </main>
  );
}
