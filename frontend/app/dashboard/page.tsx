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
        <div className="view-switcher" aria-label="Navigation principale">
          <a className="active" href="/dashboard" aria-current="page">Vue d'ensemble</a>
          <a href="/settings">Configuration IA</a>
        </div>
        <div className="topbar-actions">
          <form action="/api/auth/logout" method="post">
            <button className="ghost-button" type="submit">Déconnexion <span aria-hidden="true">↪</span></button>
          </form>
        </div>
      </nav>

      <section className="dashboard-hero single">
        <div>
          <p className="eyebrow">Espace client</p>
          <h1>Bonjour <span>{user.ownerName}</span></h1>
          <p>
            Connectez vos boîtes mail. L'agent trie et route les nouveaux emails selon vos paramètres
            en les classant et en effectuant des actions à votre place.
          </p>
        </div>
        <div className="hero-visual" aria-hidden="true">
          <div className="hero-orbit"></div>
          <div className="hero-tile hero-tile-mail">
            <svg viewBox="0 0 64 64" focusable="false">
              <rect x="10" y="16" width="44" height="32" rx="8" fill="#14B8A6" opacity="0.15" />
              <path d="M15 23.5h34v21H15z" fill="#14B8A6" />
              <path d="M15 23.5 32 36l17-12.5" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="hero-tile hero-tile-outlook">
            <ProviderIcon providerKey="hotmail" fallback="O" />
          </div>
          <div className="hero-check">✓</div>
        </div>
      </section>

      <section className="mail-grid">
        <MailCard
          providerKey="gmail"
          provider="Gmail"
          description="Connecté à un ou plusieurs comptes Google. L'agent analyse les emails reçus, les étiquette, les trie et propose les brouillons selon vos règles."
          accounts={gmailAccounts}
        />
        <MailCard
          providerKey="hotmail"
          provider="Hotmail / Outlook"
          description="Connecté à un ou plusieurs comptes Microsoft. L'agent classe et organise les emails avec des catégories et prépare des brouillons selon vos règles."
          accounts={hotmailAccounts}
        />
      </section>

      <section className="info-panel">
        <h2>Ce que fait l'agent</h2>
        <ul>
          <li>Analyse uniquement les nouveaux emails non lus, sans les marquer comme lus.</li>
          <li>Classe automatiquement avec l'IA.</li>
          <li>Applique les libellés Gmail ou les catégories Outlook.</li>
          <li>Prépare un brouillon réponse ou suggère les prochains pas.</li>
          <li>Gagne du temps et reste concentré sur l'essentiel.</li>
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
        <div className="mail-title">
          <div className="mail-icon">
            <ProviderIcon providerKey={providerKey} fallback={provider[0]} />
          </div>
          <h2>{provider}</h2>
        </div>
        <span className={connected ? "status connected" : "status pending"}>
          {connected ? "Connecté" : "Non connecté"}
        </span>
      </div>
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
                  <button className="account-action danger" type="submit">Déconnexion <span aria-hidden="true">↪</span></button>
                </form>
              ) : (
                <a className="account-action" href={`/api/accounts/connect/${providerKey}?account=${encodeURIComponent(account.account)}`}>
                  Connecter <span aria-hidden="true">⊕</span>
                </a>
              )}
            </div>
          );
        })}
      </div>

      <a className="primary-link" href={`/api/accounts/connect/${providerKey}?new=1`}>
        <span aria-hidden="true">⊕</span>
        Ajouter un autre compte {provider === "Gmail" ? "Gmail" : "Hotmail / Outlook"}
      </a>
    </article>
  );
}

function ProviderIcon({ providerKey, fallback }: { providerKey: Provider; fallback: string }) {
  if (providerKey === "hotmail") {
    return (
      <svg className="provider-logo outlook-logo" viewBox="0 0 64 64" aria-label="Outlook" role="img">
        <path fill="#28A8EA" d="M58 17.5v31.2c0 3.2-2.6 5.8-5.8 5.8H18.8c-3.2 0-5.8-2.6-5.8-5.8V17.5l22.5 16L58 17.5Z" />
        <path fill="#50D9FF" d="M13 17.5 35.5 4 58 17.5l-22.5 16L13 17.5Z" />
        <path fill="#0078D4" d="M35.5 33.5 58 17.5v31.2c0 1.1-.3 2.2-.9 3.1L35.5 36.8v-3.3Z" />
        <path fill="#0364B8" d="M13 17.5 35.5 33.5v3.3L13.9 51.8c-.6-.9-.9-2-.9-3.1V17.5Z" />
        <rect width="28" height="28" x="4" y="24" fill="#0A5DB3" rx="5.2" />
        <path fill="#FFFFFF" d="M18 44.6c-4.7 0-7.8-3.3-7.8-8.3S13.4 28 18.2 28c4.7 0 7.7 3.3 7.7 8.2 0 5.1-3.1 8.4-7.9 8.4Zm.1-3.7c2.2 0 3.5-1.8 3.5-4.6s-1.3-4.6-3.5-4.6c-2.3 0-3.6 1.8-3.6 4.6s1.3 4.6 3.6 4.6Z" />
      </svg>
    );
  }
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
