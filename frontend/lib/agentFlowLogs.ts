import fs from "node:fs";

import { dataPath } from "./paths";

export type AgentFlowLog = {
  event: string;
  timestamp: string;
  client_id: string;
  connector: string;
  account: string;
  message_id: string;
  subject: string;
  sender: string;
  label: string;
  action: string;
  priority: string;
  status: string;
  error: string;
};

export type AgentFlowGroup = {
  id: string;
  clientId: string;
  connector: string;
  account: string;
  messageId: string;
  subject: string;
  sender: string;
  lastTimestamp: string;
  status: "ok" | "warning" | "failed" | "skipped" | "started";
  label: string;
  action: string;
  steps: AgentFlowLog[];
};

export function getAgentFlowGroups(limit = 80): AgentFlowGroup[] {
  const logs = readAgentFlowLogs(limit * 8);
  const grouped = new Map<string, AgentFlowGroup>();

  for (const log of logs) {
    const id = `${log.client_id}:${log.connector}:${log.account}:${log.message_id || log.timestamp}`;
    const existing = grouped.get(id);
    if (!existing) {
      grouped.set(id, {
        id,
        clientId: log.client_id,
        connector: log.connector,
        account: log.account,
        messageId: log.message_id,
        subject: log.subject,
        sender: log.sender,
        lastTimestamp: log.timestamp,
        status: normalizeStatus(log.status),
        label: log.label,
        action: log.action,
        steps: [log],
      });
      continue;
    }

    existing.steps.push(log);
    if (Date.parse(log.timestamp) > Date.parse(existing.lastTimestamp)) {
      existing.lastTimestamp = log.timestamp;
    }
    existing.status = strongestStatus(existing.status, normalizeStatus(log.status));
    existing.subject = log.subject || existing.subject;
    existing.sender = log.sender || existing.sender;
    existing.label = log.label || existing.label;
    existing.action = log.action || existing.action;
  }

  return [...grouped.values()]
    .map((group) => ({ ...group, steps: group.steps.sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp)) }))
    .sort((a, b) => Date.parse(b.lastTimestamp) - Date.parse(a.lastTimestamp))
    .slice(0, limit);
}

function readAgentFlowLogs(limit: number): AgentFlowLog[] {
  try {
    const raw = fs.readFileSync(dataPath("agent-flow", "events.jsonl"), "utf-8");
    return raw
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .slice(-limit)
      .map((line) => JSON.parse(line) as AgentFlowLog)
      .filter((log) => log.client_id || log.event)
      .sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
  } catch {
    return [];
  }
}

function normalizeStatus(status: string): AgentFlowGroup["status"] {
  if (status === "failed") return "failed";
  if (status === "warning" || status === "guarded") return "warning";
  if (status === "skipped") return "skipped";
  if (status === "started") return "started";
  return "ok";
}

function strongestStatus(current: AgentFlowGroup["status"], next: AgentFlowGroup["status"]): AgentFlowGroup["status"] {
  const rank = { failed: 5, warning: 4, started: 3, skipped: 2, ok: 1 };
  return rank[next] > rank[current] ? next : current;
}
