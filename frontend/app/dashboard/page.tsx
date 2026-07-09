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
        <div className="mail-icon">
          <ProviderIcon providerKey={providerKey} fallback={provider[0]} />
        </div>
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

function ProviderIcon({ providerKey, fallback }: { providerKey: Provider; fallback: string }) {
  if (providerKey !== "gmail") return <span>{fallback}</span>;

  return (
    <svg className="provider-logo gmail-logo" viewBox="0 0 64 48" aria-label="Gmail" role="img">
      <path fill="#4285F4" d="M4 12.2v28.6C4 44.8 7.2 48 11.2 48H18V22.6L4 12.2Z" />
      <path fill="#34A853" d="M46 22.6V48h6.8c4 0 7.2-3.2 7.2-7.2V12.2L46 22.6Z" />
      <path fill="#FBBC04" d="M46 22.6 60 12.2v-1C60 6.7 54.9 4.1 51.2 6.8L46 10.7v11.9Z" />
      <path fill="#EA4335" d="M18 22.6 32 33.1l14-10.5V10.7L32 21.2 18 10.7v11.9Z" />
      <path fill="#C5221F" d="M4 11.2v1L18 22.6V10.7l-5.2-3.9C9.1 4.1 4 6.7 4 11.2Z" />
    </svg>
  );
}

function accountDisplayName(account: MailAccount, connected: boolean): string {
  if (account.email_address) return account.email_address;
  if (connected) return "Adresse mail à confirmer";
  return account.account === "main" ? "Compte principal" : "Compte supplémentaire";
}
