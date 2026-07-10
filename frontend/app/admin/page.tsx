import { notFound, redirect } from "next/navigation";

import { currentUser } from "@/lib/auth";
import { getClientMailAccounts, type Provider } from "@/lib/clientRegistry";
import { getDashboardActivity } from "@/lib/dashboardActivity";
import { listUsers, type DbUser } from "@/lib/db";
import { tokenFileExists } from "@/lib/paths";

type AdminClientRow = {
  user: DbUser;
  gmail: AccountSummary;
  hotmail: AccountSummary;
  activity7d: number;
  drafts7d: number;
  trashed7d: number;
};

type AccountSummary = {
  total: number;
  connected: number;
  accounts: Array<{
    account: string;
    email: string;
    connected: boolean;
  }>;
};

export default async function AdminPage() {
  const user = await currentUser();
  if (!user) redirect("/");
  if (!isAdminEmail(user.email)) notFound();

  const users = await listUsers();
  const rows = users.map(buildClientRow);
  const totalConnected = rows.reduce((sum, row) => sum + row.gmail.connected + row.hotmail.connected, 0);
  const totalProcessed = rows.reduce((sum, row) => sum + row.activity7d, 0);
  const newToday = rows.filter((row) => isToday(row.user.created_at)).length;

  return (
    <main className="admin-shell">
      <nav className="admin-topbar">
        <div>
          <p className="eyebrow">Administration InboxPilot</p>
          <h1>Monitoring plateforme</h1>
        </div>
        <a href="/dashboard">Retour espace client</a>
      </nav>

      <section className="admin-hero">
        <div>
          <p className="eyebrow">Vue sécurisée</p>
          <h2>Suivez les inscrits, les connexions mail et l'activité agent.</h2>
          <p>
            Cette page n'est visible que pour les comptes listés dans <code>ADMIN_EMAILS</code>. Les clients classiques
            reçoivent une page introuvable.
          </p>
        </div>
      </section>

      <section className="admin-stats">
        <StatCard label="Inscrits" value={String(rows.length)} />
        <StatCard label="Nouveaux aujourd'hui" value={String(newToday)} />
        <StatCard label="Boîtes connectées" value={String(totalConnected)} />
        <StatCard label="Emails classés / 7 jours" value={String(totalProcessed)} />
      </section>

      <section className="admin-panel">
        <div className="admin-section-head">
          <div>
            <p className="eyebrow">Clients</p>
            <h2>Inscrits sur la plateforme</h2>
          </div>
          <span>{rows.length} compte{rows.length > 1 ? "s" : ""}</span>
        </div>

        <div className="admin-client-list">
          {rows.map((row) => (
            <article className="admin-client-card" key={row.user.client_id}>
              <header>
                <div>
                  <h3>{row.user.owner_name}</h3>
                  <p>{row.user.email}</p>
                </div>
                <span className="admin-date">{formatDateTime(row.user.created_at)}</span>
              </header>

              <div className="admin-client-meta">
                <span>Client ID : <strong>{row.user.client_id}</strong></span>
                <span>{row.activity7d} email{row.activity7d > 1 ? "s" : ""} classé{row.activity7d > 1 ? "s" : ""} / 7 jours</span>
                <span>{row.drafts7d} brouillon{row.drafts7d > 1 ? "s" : ""}</span>
                <span>{row.trashed7d} suppression{row.trashed7d > 1 ? "s" : ""} auto</span>
              </div>

              <div className="admin-provider-grid">
                <ProviderBlock provider="gmail" title="Gmail" summary={row.gmail} />
                <ProviderBlock provider="hotmail" title="Outlook / Hotmail" summary={row.hotmail} />
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function buildClientRow(user: DbUser): AdminClientRow {
  const activity = getDashboardActivity(user.client_id);
  return {
    user,
    gmail: summarizeAccounts(user.client_id, "gmail"),
    hotmail: summarizeAccounts(user.client_id, "hotmail"),
    activity7d: activity.totalProcessed7d,
    drafts7d: activity.drafts7d,
    trashed7d: activity.trashed7d,
  };
}

function summarizeAccounts(clientId: string, provider: Provider): AccountSummary {
  const accounts = getClientMailAccounts(clientId, provider).map((account) => {
    const connected = tokenFileExists(account.token_file);
    return {
      account: account.account,
      email: account.email_address || account.account,
      connected,
    };
  });
  return {
    total: accounts.length,
    connected: accounts.filter((account) => account.connected).length,
    accounts,
  };
}

function ProviderBlock({ provider, title, summary }: { provider: Provider; title: string; summary: AccountSummary }) {
  return (
    <div className="admin-provider-block">
      <div className="admin-provider-head">
        <span className={`admin-provider-icon ${provider}`}>{provider === "gmail" ? "G" : "O"}</span>
        <strong>{title}</strong>
        <em>{summary.connected}/{summary.total} connecté{summary.connected > 1 ? "s" : ""}</em>
      </div>

      {summary.accounts.length ? (
        <ul>
          {summary.accounts.map((account) => (
            <li key={account.account}>
              <span>
                <strong>{account.email}</strong>
                <small>{account.account}</small>
              </span>
              <b className={account.connected ? "connected" : "pending"}>{account.connected ? "Connectée" : "À finaliser"}</b>
            </li>
          ))}
        </ul>
      ) : (
        <p>Aucune boîte configurée.</p>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <article>
      <strong>{value}</strong>
      <span>{label}</span>
    </article>
  );
}

function isAdminEmail(email: string): boolean {
  const admins = (process.env.ADMIN_EMAILS || "")
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
  return admins.includes(email.toLowerCase());
}

function isToday(date: Date): boolean {
  const now = new Date();
  return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate();
}

function formatDateTime(date: Date): string {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
