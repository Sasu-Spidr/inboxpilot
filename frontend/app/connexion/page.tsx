import { currentUser } from "@/lib/auth";
import { redirect } from "next/navigation";

export default async function ConnexionPage({ searchParams }: { searchParams?: Promise<{ error?: string }> }) {
  const user = await currentUser();
  const error = (await searchParams)?.error;

  if (user) {
    redirect("/dashboard");
  }

  return (
    <main className="auth-page-shell">
      <a className="marketing-brand auth-page-brand" href="/" aria-label="InboxPilot">
        <span className="marketing-logo" aria-hidden="true">
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
        </span>
        <span>InboxPilot</span>
      </a>

      <section className="marketing-auth auth-page-card">
        <div>
          <p className="marketing-badge">Créer votre espace</p>
          <h1>Lancez InboxPilot en quelques minutes.</h1>
          <p>Créez votre compte, connectez Gmail ou Outlook, puis laissez l&apos;agent classer les nouveaux emails.</p>
        </div>
        <div className="marketing-forms">
          {error && <div className="error">Vérifie les informations saisies puis réessaie.</div>}
          <form action="/api/auth/register" method="post" className="marketing-form-card">
            <h2>Créer mon espace</h2>
            <label>Prénom et nom</label>
            <input name="ownerName" placeholder="Jean Martin" required />
            <label>Email professionnel</label>
            <input name="email" type="email" placeholder="jean@entreprise.fr" required />
            <label>Mot de passe</label>
            <input name="password" type="password" minLength={8} placeholder="Minimum 8 caractères" required />
            <button type="submit">Créer et continuer →</button>
          </form>
          <form action="/api/auth/login" method="post" className="marketing-form-card compact">
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
