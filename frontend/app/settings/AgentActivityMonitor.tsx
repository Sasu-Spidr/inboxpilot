"use client";

import { useEffect, useState } from "react";

import type { ActivityEvent, DashboardActivity } from "@/lib/dashboardActivity";

type ActivityPayload = {
  connectedMailboxes: number;
  providers?: ProviderSummaries;
  activity: DashboardActivity;
};

type ProviderSummary = {
  connectedCount: number;
  accounts: string[];
};

type ProviderSummaries = {
  gmail: ProviderSummary;
  hotmail: ProviderSummary;
};

const EMPTY_PROVIDERS: ProviderSummaries = {
  gmail: { connectedCount: 0, accounts: [] },
  hotmail: { connectedCount: 0, accounts: [] },
};

export default function AgentActivityMonitor({
  initialActivity,
  initialConnectedMailboxes,
}: {
  initialActivity: DashboardActivity;
  initialConnectedMailboxes: number;
}) {
  const [payload, setPayload] = useState<ActivityPayload>({
    connectedMailboxes: initialConnectedMailboxes,
    activity: initialActivity,
  });

  useEffect(() => {
    let alive = true;
    let controller: AbortController | null = null;

    async function refresh() {
      controller?.abort();
      controller = new AbortController();
      try {
        const response = await fetch("/api/dashboard/activity", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok) return;
        const nextPayload = (await response.json()) as ActivityPayload;
        if (alive) setPayload(nextPayload);
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          console.warn("Activity refresh failed", error);
        }
      }
    }

    const interval = window.setInterval(refresh, 2000);
    refresh();

    return () => {
      alive = false;
      controller?.abort();
      window.clearInterval(interval);
    };
  }, []);

  const { connectedMailboxes, activity } = payload;
  const providers = payload.providers || EMPTY_PROVIDERS;

  return (
    <section className="agent-live-panel">
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

      <section className="provider-health-grid" aria-label="État des boîtes connectées">
        <ProviderHealthCard
          name="Gmail"
          summary={providers.gmail}
          emptyText="Aucun compte Gmail connecté."
        />
        <ProviderHealthCard
          name="Outlook / Hotmail"
          summary={providers.hotmail}
          emptyText="Aucun compte Outlook connecté."
        />
      </section>

      <RecentActivity events={activity.recent} />
    </section>
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
                <ProviderIcon provider={event.connector === "hotmail" ? "hotmail" : "gmail"} />
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

function ProviderHealthCard({
  name,
  summary,
  emptyText,
}: {
  name: string;
  summary: ProviderSummary;
  emptyText: string;
}) {
  const connected = summary.connectedCount > 0;

  return (
    <article className={connected ? "provider-health connected" : "provider-health pending"}>
      <div>
        <span className="provider-health-dot" />
        <strong>{name}</strong>
      </div>
      <p>
        {connected
          ? `${summary.connectedCount} boîte${summary.connectedCount > 1 ? "s" : ""} active${summary.connectedCount > 1 ? "s" : ""}`
          : emptyText}
      </p>
      {connected && (
        <ul>
          {summary.accounts.slice(0, 3).map((account) => (
            <li key={account}>{account}</li>
          ))}
          {summary.accounts.length > 3 && <li>+{summary.accounts.length - 3} autre(s)</li>}
        </ul>
      )}
    </article>
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
