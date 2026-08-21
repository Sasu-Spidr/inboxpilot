import Link from "next/link";
import { redirect } from "next/navigation";

import AgentActivityMonitor from "./AgentActivityMonitor";
import LabelSettingsForm from "./LabelSettingsForm";
import { canAccessAdmin, currentUser, isAdmin } from "@/lib/auth";
import { getClientMailAccounts, type Provider } from "@/lib/clientRegistry";
import { getClientSettings } from "@/lib/clientSettings";
import { getDashboardActivity } from "@/lib/dashboardActivity";
import { mfaFeatureEnabled } from "@/lib/features";
import { tokenFileExists } from "@/lib/paths";

type SettingsSearchParams = {
  saved?: string;
  mfa?: string;
  provider?: string;
  account?: string;
};

export default async function SettingsPage({ searchParams }: { searchParams?: Promise<SettingsSearchParams> }) {
  const user = await currentUser();
  if (!user) redirect("/");

  const params = await searchParams;
  const gmailAccounts = getClientMailAccounts(user.clientId, "gmail");
  const hotmailAccounts = getClientMailAccounts(user.clientId, "hotmail");
  const accounts = [
    ...gmailAccounts.map((account) => ({ ...account, provider: "gmail" as const })),
    ...hotmailAccounts.map((account) => ({ ...account, provider: "hotmail" as const })),
  ];
  const connectedMailboxes = accounts.filter((mailbox) => tokenFileExists(mailbox.token_file)).length;
  const selectedMailbox =
    accounts.find((mailbox) => mailbox.provider === params?.provider && mailbox.account === params?.account) ||
    accounts.find((mailbox) => tokenFileExists(mailbox.token_file)) ||
    accounts[0] ||
    null;
  const settings = getClientSettings(user.clientId, selectedMailbox?.provider, selectedMailbox?.account);
  const activity = getDashboardActivity(user.clientId);
  const saved = params?.saved === "1";

  return (
    <main className="dashboard-shell settings-shell">
      <nav className="topbar">
        <div className="view-switcher" aria-label="Navigation principale">
          <Link href="/dashboard">Vue d'ensemble</Link>
          <Link className="active" href="/settings" aria-current="page">
            Configuration IA
          </Link>
        </div>
        {isAdmin(user) && (
          <div className="topbar-actions">
            <Link className="ghost-button" href={canAccessAdmin(user) ? "/73948261502839476150" : "/mfa/setup"}>
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

      {saved && <div className="success-banner">Paramètres enregistrés. La boîte sélectionnée est synchronisée.</div>}

      {mfaFeatureEnabled() && params?.mfa === "enabled" && <div className="success-banner">Double authentification activ&eacute;e.</div>}
      {mfaFeatureEnabled() && params?.mfa === "disabled" && <div className="success-banner">Double authentification d&eacute;sactiv&eacute;e.</div>}
      {mfaFeatureEnabled() && params?.mfa === "disable-error" && <div className="error-banner">Code MFA invalide. La double authentification reste active.</div>}

      <AgentActivityMonitor
        initialActivity={activity}
        initialConnectedMailboxes={connectedMailboxes}
        labelColors={Object.fromEntries(settings.labels.map((label) => [label.key, label.color]))}
      />

      {mfaFeatureEnabled() && <MfaSecurityCard enabled={user.mfaEnabled} />}

      <section className="mailbox-settings-card">
        <div className="mailbox-settings-heading">
          <p className="eyebrow">Boîte à configurer</p>
          <h2>Choisissez l'adresse concernée</h2>
          <p>Chaque boîte Gmail ou Outlook peut avoir ses propres libellés, couleurs et actions.</p>
        </div>
        <div className="mailbox-settings-list">
          {accounts.map((mailbox) => {
            const isActive = selectedMailbox?.provider === mailbox.provider && selectedMailbox.account === mailbox.account;
            const isConnected = tokenFileExists(mailbox.token_file);
            return (
              <Link
                key={`${mailbox.provider}:${mailbox.account}`}
                className={`mailbox-settings-option${isActive ? " active" : ""}`}
                href={`/settings?provider=${mailbox.provider}&account=${encodeURIComponent(mailbox.account)}`}
                scroll={false}
              >
                <ProviderIcon provider={mailbox.provider} />
                <span>
                  <strong>{mailbox.email_address || mailboxLabel(mailbox.provider, mailbox.account)}</strong>
                  <small>{mailboxLabel(mailbox.provider, mailbox.account)} · {isConnected ? "Connectée" : "Connexion à finaliser"}</small>
                </span>
              </Link>
            );
          })}
        </div>
      </section>

      <LabelSettingsForm
        key={`${selectedMailbox?.provider || "global"}:${selectedMailbox?.account || "global"}`}
        initialLabels={settings.labels}
        selectedProvider={selectedMailbox?.provider}
        selectedAccount={selectedMailbox?.account}
        selectedMailboxLabel={selectedMailbox ? selectedMailbox.email_address || mailboxLabel(selectedMailbox.provider, selectedMailbox.account) : "Configuration globale"}
      />
    </main>
  );
}

function MfaSecurityCard({ enabled }: { enabled: boolean }) {
  return (
    <section className="security-settings-card">
      <div>
        <p className="eyebrow">S&eacute;curit&eacute;</p>
        <h2>Double authentification</h2>
        <p>Ajoutez un code &agrave; 6 chiffres apr&egrave;s le mot de passe pour prot&eacute;ger l'acc&egrave;s &agrave; votre espace.</p>
      </div>
      {enabled ? (
        <form action="/api/auth/mfa/disable" method="post" className="mfa-disable-form">
          <span className="status connected">Activ&eacute;e</span>
          <input name="code" inputMode="numeric" autoComplete="one-time-code" placeholder="Code MFA" required />
          <button className="ghost-button danger" type="submit">D&eacute;sactiver</button>
        </form>
      ) : (
        <a className="primary-link security-link" href="/mfa/setup">
          Activer la double authentification
        </a>
      )}
    </section>
  );
}

function mailboxLabel(provider: Provider, account: string) {
  if (account === "main") return provider === "gmail" ? "Gmail 1" : "Outlook 1";
  return account.replace(/^gmail-/, "Gmail ").replace(/^hotmail-/, "Outlook ");
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
