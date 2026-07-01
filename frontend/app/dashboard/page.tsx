import { redirect } from "next/navigation";

import { currentUser } from "@/lib/auth";
import { tokenExists } from "@/lib/paths";

export default async function Dashboard() {
  const user = await currentUser();
  if (!user) redirect("/");

  const gmailConnected = tokenExists(user.clientId, "gmail");
  const hotmailConnected = tokenExists(user.clientId, "hotmail");

  return (
    <main className="dashboard-shell">
      <nav className="topbar">
        <div>
          <span className="brand-dot" />
          <strong>SPIDR Mail Agent</strong>
        </div>
        <form action="/api/auth/logout" method="post">
          <button className="ghost-button" type="submit">Déconnexion</button>
        </form>
      </nav>

      <section className="dashboard-hero single">
        <div>
          <p className="eyebrow">Espace client</p>
          <h1>Bonjour {user.ownerName}</h1>
          <p>
            Connectez vos boîtes mail. L'agent traite ensuite les nouveaux emails en arrière-plan :
            tri, labels et brouillons prêts à valider.
          </p>
        </div>
      </section>

      <section className="mail-grid">
        <MailCard
          provider="Gmail"
          description="Connectez un compte Google pour lire les emails non lus, appliquer les labels et créer les brouillons."
          connected={gmailConnected}
          href="/api/accounts/connect/gmail"
        />
        <MailCard
          provider="Hotmail / Outlook"
          description="Connectez un compte Microsoft pour classer Outlook/Hotmail avec les catégories et brouillons."
          connected={hotmailConnected}
          href="/api/accounts/connect/hotmail"
        />
      </section>

      <section className="info-panel">
        <h2>Ce que fait l'agent</h2>
        <ul>
          <li>Lit uniquement les nouveaux emails non lus.</li>
          <li>Classe automatiquement avec l'IA.</li>
          <li>Applique les labels Gmail ou catégories Outlook.</li>
          <li>Crée un brouillon lorsque c'est nécessaire.</li>
          <li>N'envoie jamais d'email automatiquement.</li>
        </ul>
      </section>
    </main>
  );
}

function MailCard({
  provider,
  description,
  connected,
  href,
}: {
  provider: string;
  description: string;
  connected: boolean;
  href: string;
}) {
  return (
    <article className="mail-card">
      <div className="mail-card-head">
        <div className="mail-icon">{provider[0]}</div>
        <span className={connected ? "status connected" : "status pending"}>
          {connected ? "Connecté" : "Non connecté"}
        </span>
      </div>
      <h2>{provider}</h2>
      <p>{description}</p>
      <a className="primary-link" href={href}>
        {connected ? "Reconnecter" : "Connecter"} {provider}
      </a>
    </article>
  );
}
