import fs from "node:fs";

import { dataPath } from "./paths";

export type ActivityEvent = {
  client_id: string;
  connector: "gmail" | "hotmail" | string;
  account: string;
  message_id: string;
  subject: string;
  sender: string;
  label: string;
  action: string;
  draft_created: boolean;
  processed_at: string;
};

export type DashboardActivity = {
  totalProcessed7d: number;
  drafts7d: number;
  trashed7d: number;
  recent: ActivityEvent[];
};

export function getDashboardActivity(clientId: string): DashboardActivity {
  const events = readActivityEvents(clientId);
  const since = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const recent7d = events.filter((event) => eventTimestamp(event) >= since);

  return {
    totalProcessed7d: recent7d.length,
    drafts7d: recent7d.filter((event) => event.draft_created || event.action === "draft").length,
    trashed7d: recent7d.filter((event) => event.action === "trash").length,
    recent: events.slice(0, 5),
  };
}

function readActivityEvents(clientId: string): ActivityEvent[] {
  try {
    const raw = fs.readFileSync(dataPath("activity", "events.jsonl"), "utf-8");
    return raw
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => JSON.parse(line) as ActivityEvent)
      .filter((event) => event.client_id === clientId)
      .sort((a, b) => eventTimestamp(b) - eventTimestamp(a));
  } catch {
    return [];
  }
}

function eventTimestamp(event: ActivityEvent): number {
  const timestamp = Date.parse(event.processed_at);
  return Number.isFinite(timestamp) ? timestamp : 0;
}
