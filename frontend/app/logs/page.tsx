import { notFound, redirect } from "next/navigation";

import { canAccessAdmin, currentUser } from "@/lib/auth";
import { getAgentFlowGroups, type AgentFlowGroup, type AgentFlowLog } from "@/lib/agentFlowLogs";

const EVENT_LABELS: Record<string, string> = {
  email_detected: "Email détecté",
  email_skipped_before_activation: "Ignoré : avant activation",
  email_classified: "Classification IA",
  label_applied: "Libellé appliqué",
  draft_created: "Brouillon préparé",
  email_trashed: "Email supprimé",
  email_archived: "Email archivé",
  email_left_unread: "Conservé non lu",
  email_moved: "Email déplacé",
  unread_expired_deleted: "Suppression différée",
  processed_email_label_reconciled: "Libellé synchronisé",
  email_already_processed: "Déjà traité",
  processing_failed: "Erreur de traitement",
  polling_failed: "Erreur de réception",
  label_color_sync_failed: "Erreur couleur libellé",
};

export default async function LogsPage() {
  const user = await currentUser();
  if (!user) redirect("/");
  if (!canAccessAdmin(user)) notFound();

  const groups = getAgentFlowGroups(80);
  const running = groups.filter((group) => group.status === "started").length;
  const failed = groups.filter((group) => group.status === "failed").length;
  const labeled = groups.filter((group) => group.steps.some((step) => step.event === "label_applied")).length;
  const actions = groups.filter((group) => group.action && group.action !== "keep").length;

  return (
    <main className="logs-shell">
      <nav className="logs-topbar">
        <div>
          <p className="eyebrow">Logs InboxPilot</p>
          <h1>Journal de traitement agent</h1>
        </div>
        <div className="logs-actions">
          <a href="/73948261502839476150">Admin</a>
          <a href="/dashboard">Espace client</a>
        </div>
      </nav>

      <section className="logs-hero">
        <div>
          <p className="eyebrow">Réception → IA → libellé → action</p>
          <h2>Chaque email traité laisse une trace claire.</h2>
          <p>
            Cette vue permet de contrôler ce que l'agent fait réellement : réception de l'email, décision du modèle,
            libellé appliqué, brouillon ou suppression éventuelle.
          </p>
        </div>
      </section>

      <section className="logs-stats" aria-label="Résumé des logs">
        <StatCard value={String(groups.length)} label="Emails suivis" />
        <StatCard value={String(labeled)} label="Libellés appliqués" />
        <StatCard value={String(actions)} label="Actions effectuées" />
        <StatCard value={String(failed)} label="Erreurs" />
        <StatCard value={String(running)} label="En cours" />
      </section>

      <section className="logs-panel">
        <div className="logs-section-head">
          <div>
            <p className="eyebrow">Flux récent</p>
            <h2>Derniers traitements</h2>
          </div>
          <span>{groups.length} entrée{groups.length > 1 ? "s" : ""}</span>
        </div>

        {groups.length ? (
          <div className="flow-list">
            {groups.map((group) => (
              <FlowCard group={group} key={group.id} />
            ))}
          </div>
        ) : (
          <div className="logs-empty">
            <strong>Aucun log agent pour le moment.</strong>
            <p>Dès qu'un nouveau cycle worker traite un email, il apparaîtra ici.</p>
          </div>
        )}
      </section>
    </main>
  );
}

function FlowCard({ group }: { group: AgentFlowGroup }) {
  return (
    <article className={`flow-card ${group.status}`}>
      <header>
        <div>
          <span className="flow-provider">{providerLabel(group.connector)}</span>
          <h3>{group.subject || group.clientId || "Email sans sujet"}</h3>
          <p>
            {group.sender ? `${group.sender} · ` : ""}
            {providerAccountLabel(group.connector, group.account)}
            {group.messageId ? ` · ${shortId(group.messageId)}` : ""}
          </p>
        </div>
        <div className="flow-summary">
          {group.label ? <span className="flow-label">{group.label}</span> : null}
          {group.action ? <span className="flow-action">{actionLabel(group.action)}</span> : null}
          <time>{formatDateTime(group.lastTimestamp)}</time>
        </div>
      </header>

      <ol className="flow-steps">
        {group.steps.map((step, index) => (
          <FlowStep step={step} key={`${step.event}-${step.timestamp}-${index}`} />
        ))}
      </ol>
    </article>
  );
}

function FlowStep({ step }: { step: AgentFlowLog }) {
  return (
    <li className={`flow-step ${step.status || "ok"}`}>
      <span className="flow-step-dot" />
      <div>
        <strong>{EVENT_LABELS[step.event] || step.event}</strong>
        <p>{stepDetail(step)}</p>
        {step.error ? <pre>{step.error}</pre> : null}
      </div>
      <time>{formatTime(step.timestamp)}</time>
    </li>
  );
}

function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <article>
      <strong>{value}</strong>
      <span>{label}</span>
    </article>
  );
}

function stepDetail(step: AgentFlowLog): string {
  const details = [
    step.label ? `Libellé : ${step.label}` : "",
    step.action ? `Action : ${actionLabel(step.action)}` : "",
    step.priority ? `Priorité : ${step.priority}` : "",
    step.status ? `Statut : ${statusLabel(step.status)}` : "",
  ].filter(Boolean);
  return details.join(" · ") || "Événement enregistré.";
}

function providerLabel(connector: string): string {
  if (connector === "hotmail") return "Outlook";
  if (connector === "gmail") return "Gmail";
  return connector || "Agent";
}

function providerAccountLabel(connector: string, account: string): string {
  return `${providerLabel(connector)}${account ? ` · ${account}` : ""}`;
}

function actionLabel(action: string): string {
  return (
    {
      keep: "Aucune action",
      draft: "Brouillon",
      trash: "Suppression",
      trash_unread_expired: "Suppression différée",
      archive: "Archive",
      mark_read: "Marquer comme lu",
      move: "Déplacement",
      skip: "Ignoré",
    }[action] || action
  );
}

function statusLabel(status: string): string {
  return (
    {
      ok: "OK",
      started: "Démarré",
      skipped: "Ignoré",
      warning: "Attention",
      guarded: "Protégé",
      failed: "Erreur",
    }[status] || status
  );
}

function shortId(value: string): string {
  return value.length > 16 ? `${value.slice(0, 8)}…${value.slice(-6)}` : value;
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date inconnue";
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--:--";
  return new Intl.DateTimeFormat("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}
