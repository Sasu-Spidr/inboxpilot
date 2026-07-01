import { redirect } from "next/navigation";

import { currentUser } from "@/lib/auth";

export default async function Home({ searchParams }: { searchParams?: Promise<{ error?: string }> }) {
  if (await currentUser()) redirect("/dashboard");

  const error = (await searchParams)?.error;

  return (
    <main className="auth-shell">
      <section className="hero-card">
        <div className="brand-pill">SPIDR Mail Agent</div>
        <h1>Connectez vos boîtes mail. Laissez l'agent trier le reste.</h1>
        <p>
          Gmail et Outlook connectés proprement, emails classés, labels appliqués et brouillons prêts à relire.
          Aucun email n'est envoyé automatiquement.
        </p>
        <div className="feature-grid">
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
            <button type="submit">Créer et continuer</button>
          </form>

          <form action="/api/auth/login" method="post" className="form-card secondary">
            <h2>Déjà inscrit</h2>
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
