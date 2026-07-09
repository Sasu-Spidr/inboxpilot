import { redirect } from "next/navigation";

import { currentUser } from "@/lib/auth";

export default async function Home({ searchParams }: { searchParams?: Promise<{ error?: string }> }) {
  if (await currentUser()) redirect("/dashboard");

  const error = (await searchParams)?.error;

  return (
    <main className="auth-shell">
      <section className="hero-card" aria-label="Présentation InboxPilot">
        <div className="brand-pill">
          <span className="brand-icon" aria-hidden="true">◆</span>
          <span>InboxPilot</span>
        </div>

        <div className="hero-copy">
          <p className="eyebrow">Agent email autonome</p>
          <h1>
            Connectez vos boîtes. <span>L'agent trie le reste.</span>
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
        {error && <div className="error">Vérifie les informations saisies puis réessaie.</div>}
        <div className="forms">
          <form action="/api/auth/register" method="post" className="form-card">
            <h2>Créer mon espace</h2>
            <label>Prénom et nom</label>
            <input name="ownerName" placeholder="Jean Martin" required />
            <label>Email professionnel</label>
            <input name="email" type="email" placeholder="jean@entreprise.fr" required />
            <label>Mot de passe</label>
            <input name="password" type="password" minLength={8} placeholder="Minimum 8 caractères" required />
            <button type="submit">Créer et continuer →</button>
            <p className="form-switch">
              Déjà inscrit ? <a href="#connexion">Se connecter</a>
            </p>
          </form>

          <form id="connexion" action="/api/auth/login" method="post" className="form-card secondary">
            <h2>Se connecter</h2>
            <label>Email</label>
            <input name="email" type="email" placeholder="jean@entreprise.fr" required />
            <label>Mot de passe</label>
            <input name="password" type="password" required />
            <button type="submit">Se connecter</button>
          </form>
        </div>
      </section>
    </main>
  );
}
