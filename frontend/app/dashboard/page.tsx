import { redirect } from "next/navigation";

import { currentUser } from "@/lib/auth";
import { getClientMailAccounts, type MailAccount, type Provider } from "@/lib/clientRegistry";
import { getDashboardActivity, type ActivityEvent } from "@/lib/dashboardActivity";
import { tokenFileExists } from "@/lib/paths";

export default async function Dashboard() {
  const user = await currentUser();
  if (!user) redirect("/");

  const gmailAccounts = getClientMailAccounts(user.clientId, "gmail");
  const hotmailAccounts = getClientMailAccounts(user.clientId, "hotmail");
  const connectedMailboxes = [...gmailAccounts, ...hotmailAccounts].filter((account) => tokenFileExists(account.token_file)).length;
  const activity = getDashboardActivity(user.clientId);

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

      <section className="agent-overview">
        <div className="agent-status-card">
          <p className="eyebrow">Agent InboxPilot</p>
          <h2>{agentStatusTitle(connectedMailboxes, activity.totalProcessed7d)}</h2>
          <p>{agentStatusText(connectedMailboxes, activity.totalProcessed7d)}</p>
        </div>
        <div className="stats-grid">
          <StatCard value={String(connectedMailboxes)} label="Boîtes connectées" />
          <StatCard value={String(activity.totalProcessed7d)} label="Emails classés / 7 jours" />
          <StatCard value={String(activity.drafts7d)} label="Brouillons préparés" />
          <StatCard value={String(activity.trashed7d)} label="Suppressions auto" />
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

      <RecentActivity events={activity.recent} />

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

function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <article className="stat-card">
      <strong>{value}</strong>
      <span>{label}</span>
    </article>
  );
}

function RecentActivity({ events }: { events: ActivityEvent[] }) {
  return (
    <section className="activity-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Activité récente</p>
          <h2>Ce que l'agent a traité</h2>
        </div>
      </div>

      {events.length ? (
        <div className="activity-list">
          {events.map((event) => (
            <article className="activity-item" key={`${event.connector}-${event.account}-${event.message_id}`}>
              <div className="activity-provider">
                <ProviderIcon providerKey={event.connector === "hotmail" ? "hotmail" : "gmail"} fallback={event.connector[0]?.toUpperCase() || "M"} />
              </div>
              <div className="activity-content">
                <strong>{event.subject || "Sans objet"}</strong>
                <span>{event.sender || "Expéditeur inconnu"}</span>
              </div>
              <div className="activity-meta">
                <span className="activity-label">{event.label}</span>
                <small>{actionLabel(event)}</small>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="activity-empty">
          <strong>Aucune activité pour le moment.</strong>
          <p>Dès que de nouveaux emails non lus seront traités, ils apparaîtront ici avec le libellé et l'action appliquée.</p>
        </div>
      )}
    </section>
  );
}

function agentStatusTitle(connectedMailboxes: number, totalProcessed7d: number): string {
  if (!connectedMailboxes) return "Connectez une boîte mail pour activer l'agent.";
  if (!totalProcessed7d) return "L'agent est actif et prêt à classer les prochains emails.";
  return `L'agent a classé ${totalProcessed7d} email${totalProcessed7d > 1 ? "s" : ""} cette semaine.`;
}

function agentStatusText(connectedMailboxes: number, totalProcessed7d: number): string {
  if (!connectedMailboxes) return "Ajoutez Gmail ou Outlook pour lancer automatiquement le tri des nouveaux emails non lus.";
  const mailboxText = `${connectedMailboxes} boîte${connectedMailboxes > 1 ? "s" : ""} mail connectée${connectedMailboxes > 1 ? "s" : ""}`;
  if (!totalProcessed7d) return `${mailboxText}. InboxPilot attend les prochains emails non lus pour appliquer vos libellés et vos règles.`;
  return `${mailboxText}. InboxPilot continue d'analyser uniquement les nouveaux emails non lus, sans les marquer comme lus.`;
}

function actionLabel(event: ActivityEvent): string {
  if (event.draft_created || event.action === "draft") return "Brouillon préparé";
  if (event.action === "trash") return "Supprimé selon vos règles";
  if (event.action === "archive") return "Archivé";
  return "Libellé appliqué";
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
