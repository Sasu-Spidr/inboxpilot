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
          <strong>InboxPilot</strong>
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
            Connectez vos boîtes mail. L'agent traite ensuite les nouveaux emails non lus en arrière-plan :
            tri, libellés et brouillons selon vos paramètres.
          </p>
        </div>
      </section>

      <section className="mail-grid">
        <MailCard
          providerKey="gmail"
          provider="Gmail"
          description="Connectez un ou plusieurs comptes Google. L'agent analyse les emails non lus, applique les libellés et prépare les brouillons selon vos réglages."
          accounts={gmailAccounts}
        />
        <MailCard
          providerKey="hotmail"
          provider="Hotmail / Outlook"
          description="Connectez un ou plusieurs comptes Microsoft. L'agent classe Outlook/Hotmail avec les catégories et prépare les brouillons selon vos réglages."
          accounts={hotmailAccounts}
        />
      </section>

      <section className="info-panel">
        <h2>Ce que fait l'agent</h2>
        <ul>
          <li>Analyse uniquement les nouveaux emails non lus, sans les marquer comme lus.</li>
          <li>Classe automatiquement avec l'IA.</li>
          <li>Applique les libellés Gmail ou les catégories Outlook.</li>
          <li>Prépare un brouillon lorsque vos paramètres le demandent.</li>
          <li>Les réponses et suppressions automatiques suivent uniquement les paramètres définis par vous.</li>
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
                <strong>{accountDisplayName(account, accountConnected)}</strong>
                <span>{accountConnected ? "Agent actif sur cette boîte" : "Connexion à finaliser"}</span>
              </div>
              {accountConnected ? (
                <form action={`/api/accounts/disconnect/${providerKey}?account=${encodeURIComponent(account.account)}`} method="post">
                  <button className="account-action danger" type="submit">Déconnexion</button>
                </form>
              ) : (
                <a className="account-action" href={`/api/accounts/connect/${providerKey}?account=${encodeURIComponent(account.account)}`}>
                  Connecter
                </a>
              )}
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

function accountDisplayName(account: MailAccount, connected: boolean): string {
  if (account.email_address) return account.email_address;
  if (connected) return "Adresse mail à confirmer";
  return account.account === "main" ? "Compte principal" : "Compte supplémentaire";
}
