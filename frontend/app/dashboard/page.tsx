import { redirect } from "next/navigation";

import { currentUser } from "@/lib/auth";
import { getClientMailAccounts, type MailAccount, type Provider } from "@/lib/clientRegistry";
import { tokenFileExists } from "@/lib/paths";

export default async function Dashboard() {
  const user = await currentUser();
  if (!user) redirect("/");

  const gmailAccounts = getClientMailAccounts(user.clientId, "gmail");
  const hotmailAccounts = getClientMailAccounts(user.clientId, "hotmail");

  return (
    <main className="dashboard-shell">
      <nav className="topbar">
        <div>
          <span className="brand-dot" />
          <strong>SPIDR Mail Agent</strong>
        </div>
        <div className="topbar-actions">
          <a className="ghost-button" href="/settings">Paramètres</a>
          <form action="/api/auth/logout" method="post">
            <button className="ghost-button" type="submit">Déconnexion</button>
          </form>
        </div>
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
          providerKey="gmail"
          provider="Gmail"
          description="Connectez un ou plusieurs comptes Google pour lire les emails non lus, appliquer les labels et créer les brouillons."
          accounts={gmailAccounts}
        />
        <MailCard
          providerKey="hotmail"
          provider="Hotmail / Outlook"
          description="Connectez un ou plusieurs comptes Microsoft pour classer Outlook/Hotmail avec les catégories et brouillons."
          accounts={hotmailAccounts}
        />
      </section>

      <section className="info-panel">
        <h2>Ce que fait l'agent</h2>
        <ul>
          <li>Lit uniquement les nouveaux emails non lus.</li>
          <li>Classe automatiquement avec l'IA.</li>
          <li>Applique les labels Gmail ou catégories Outlook.</li>
          <li>Crée un brouillon lorsque c'est nécessaire.</li>
          <li>Réponses et suppressions selon les paramètres définis par vous.</li>
        </ul>
      </section>
    </main>
  );
}

function MailCard({
  providerKey,
  provider,
  description,
  accounts,
}: {
  providerKey: Provider;
  provider: string;
  description: string;
  accounts: MailAccount[];
}) {
  const connectedCount = accounts.filter((account) => tokenFileExists(account.token_file)).length;
  const connected = connectedCount > 0;

  return (
    <article className="mail-card">
      <div className="mail-card-head">
        <div className="mail-icon">{provider[0]}</div>
        <span className={connected ? "status connected" : "status pending"}>
          {connected ? `${connectedCount} connecté${connectedCount > 1 ? "s" : ""}` : "Non connecté"}
        </span>
      </div>
      <h2>{provider}</h2>
      <p>{description}</p>

      <div className="account-list">
        {accounts.map((account) => {
          const accountConnected = tokenFileExists(account.token_file);
          return (
            <div className="account-item" key={account.account}>
              <div>
                <strong>{account.email_address || (account.account === "main" ? "Compte principal" : account.account)}</strong>
                <span>{accountConnected ? "Agent actif sur cette boîte" : "Connexion à finaliser"}</span>
              </div>
              <a href={`/api/accounts/connect/${providerKey}?account=${encodeURIComponent(account.account)}`}>
                {accountConnected ? "Reconnecter" : "Connecter"}
              </a>
            </div>
          );
        })}
      </div>

      <a className="primary-link" href={`/api/accounts/connect/${providerKey}?new=1`}>
        Ajouter un autre compte {provider}
      </a>
    </article>
  );
}
