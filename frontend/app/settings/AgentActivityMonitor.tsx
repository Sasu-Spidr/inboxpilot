"use client";

import { useEffect, useState } from "react";

import type { ActivityEvent, DashboardActivity } from "@/lib/dashboardActivity";

type ActivityPayload = {
  connectedMailboxes: number;
  activity: DashboardActivity;
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
        <span className="live-sync-badge">Synchro auto · 2s</span>
      </div>

      {events.length ? (
        <div className="activity-list">
          {events.map((event) => (
            <article className="activity-item" key={`${event.connector}-${event.account}-${event.message_id}`}>
              <div className="activity-provider">{event.connector === "hotmail" ? "O" : "G"}</div>
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
