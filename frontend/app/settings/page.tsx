import Link from "next/link";
import { redirect } from "next/navigation";

import AgentActivityMonitor from "./AgentActivityMonitor";
import { currentUser, isAdmin } from "@/lib/auth";
import { getClientMailAccounts } from "@/lib/clientRegistry";
import { getClientSettings, type LabelSetting } from "@/lib/clientSettings";
import { getDashboardActivity } from "@/lib/dashboardActivity";
import { tokenFileExists } from "@/lib/paths";

export default async function SettingsPage({ searchParams }: { searchParams?: Promise<{ saved?: string }> }) {
  const user = await currentUser();
  if (!user) redirect("/");

  const settings = getClientSettings(user.clientId);
  const gmailAccounts = getClientMailAccounts(user.clientId, "gmail");
  const hotmailAccounts = getClientMailAccounts(user.clientId, "hotmail");
  const accounts = [...gmailAccounts, ...hotmailAccounts];
  const connectedMailboxes = accounts.filter((account) => tokenFileExists(account.token_file)).length;
  const activity = getDashboardActivity(user.clientId);
  const saved = (await searchParams)?.saved === "1";

  return (
    <main className="dashboard-shell settings-shell">
      <nav className="topbar">
        <div className="view-switcher" aria-label="Navigation principale">
          <Link href="/dashboard">Vue d'ensemble</Link>
          <Link className="active" href="/settings" aria-current="page">Configuration IA</Link>
        </div>
        {isAdmin(user) && (
          <div className="topbar-actions">
            <Link className="ghost-button" href="/73948261502839476150">
              Admin
            </Link>
          </div>
        )}
      </nav>

      <section className="dashboard-hero settings-hero">
        <div>
          <p className="eyebrow">Module de paramètres</p>
          <h1>Libellés et automatisations</h1>
          <p>
            Configurez les libellés visibles par l'agent, leur couleur et les actions à effectuer automatiquement
            pour votre espace client.
          </p>
        </div>

        <div className="hero-visual settings-hero-visual" aria-hidden="true">
          <div className="hero-orbit" />
          <div className="hero-tile hero-tile-mail">
            <ProviderIcon provider="gmail" />
          </div>
          <div className="hero-tile hero-tile-outlook">
            <ProviderIcon provider="hotmail" />
          </div>
          <div className="hero-check">✦</div>
        </div>
      </section>

      {saved && <div className="success-banner">Paramètres enregistrés. L'agent utilisera ces réglages au prochain cycle.</div>}

      <AgentActivityMonitor initialActivity={activity} initialConnectedMailboxes={connectedMailboxes} />

      <form action="/api/settings/labels" method="post" className="settings-panel">
        <input type="hidden" name="labelCount" value={settings.labels.length} />
        <div className="settings-toolbar">
          <div>
            <p className="eyebrow">Réglages des libellés</p>
            <strong>Personnalisez les règles de tri</strong>
            <span>Modifiez vos préférences puis enregistrez pour les appliquer au prochain cycle.</span>
          </div>
          <button type="submit">Enregistrer les paramètres</button>
        </div>

        <div className="settings-list">
          {settings.labels.map((label, index) => (
            <details className="settings-row" key={label.key} open={index === 0}>
              <summary className="settings-row-summary">
                <span className="label-preview">
                  <span className="label-color-dot" style={{ backgroundColor: label.color }} />
                  <span>
                    <strong>{label.key}</strong>
                    <small>{label.description}</small>
                  </span>
                </span>
                <span className="active-rules-count">
                  {activeRulesCount(label)} action{activeRulesCount(label) > 1 ? "s" : ""} active{activeRulesCount(label) > 1 ? "s" : ""}
                </span>
              </summary>

              <div className="settings-row-body">
                <input type="hidden" name={`labels.${index}.key`} value={label.key} />

                <label className="setting-field">
                  Nom affiché
                  <input name={`labels.${index}.name`} defaultValue={label.name} maxLength={64} required />
                </label>

                <label className="setting-field color-field">
                  Couleur
                  <input name={`labels.${index}.color`} type="color" defaultValue={label.color} />
                </label>

                <label className="setting-field description-field">
                  Description
                  <textarea name={`labels.${index}.description`} defaultValue={label.description} maxLength={240} rows={2} required />
                </label>

                <div className="toggle-grid">
                  <label>
                    <input name={`labels.${index}.prepareDraft`} type="checkbox" defaultChecked={label.prepareDraft} />
                    Préparer un brouillon
                  </label>
                  <label>
                    <input name={`labels.${index}.autoReply`} type="checkbox" defaultChecked={label.autoReply} />
                    Réponse auto
                  </label>
                  <label>
                    <input name={`labels.${index}.autoDelete`} type="checkbox" defaultChecked={label.autoDelete} />
                    Suppression auto
                  </label>
                </div>
              </div>
            </details>
          ))}
        </div>

        <div className="settings-actions">
          <p>Les réponses et suppressions automatiques suivent uniquement les paramètres définis par vous.</p>
        </div>
      </form>
    </main>
  );
}

function activeRulesCount(label: LabelSetting) {
  return Number(label.prepareDraft) + Number(label.autoReply) + Number(label.autoDelete);
}

function ProviderIcon({ provider }: { provider: "gmail" | "hotmail" }) {
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
