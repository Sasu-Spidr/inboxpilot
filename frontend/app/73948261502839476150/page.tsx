import { notFound, redirect } from "next/navigation";

import { currentUser, isAdmin } from "@/lib/auth";
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
  if (!isAdmin(user)) notFound();

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
            Cette page n'est visible que pour les comptes ayant le rôle administrateur. Les clients classiques
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
        <span className={`admin-provider-icon ${provider}`}>
          <ProviderIcon provider={provider} />
        </span>
        <strong>{title}</strong>
        <em>{summary.connected}/{summary.total} connecté{summary.connected > 1 ? "s" : ""}</em>
      </div>

      {summary.accounts.length ? (
        <ul>
          {summary.accounts.map((account, index) => (
            <li key={account.account}>
              <span>
                <strong>{account.email}</strong>
                <small>{providerAccountLabel(provider, index)}</small>
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

function providerAccountLabel(provider: Provider, index: number): string {
  return `${provider === "gmail" ? "Gmail" : "Outlook"} ${index + 1}`;
}

function ProviderIcon({ provider }: { provider: Provider }) {
  if (provider === "hotmail") {
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

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <article>
      <strong>{value}</strong>
      <span>{label}</span>
    </article>
  );
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
