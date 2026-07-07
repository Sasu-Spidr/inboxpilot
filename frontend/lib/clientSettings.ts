import fs from "node:fs";
import path from "node:path";

import { dataPath } from "./paths";

export type LabelSetting = {
  key: string;
  name: string;
  color: string;
  prepareDraft: boolean;
  autoReply: boolean;
  autoDelete: boolean;
};

export type ClientSettings = {
  labels: LabelSetting[];
  updatedAt: string;
};

export const DEFAULT_LABEL_SETTINGS: LabelSetting[] = [
  { key: "À traiter", name: "À traiter", color: "#8b8b7a", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "À répondre", name: "À répondre", color: "#0d9488", prepareDraft: true, autoReply: false, autoDelete: false },
  { key: "Relance", name: "Relance", color: "#f97316", prepareDraft: true, autoReply: false, autoDelete: false },
  { key: "Commentaire", name: "Commentaire", color: "#eab308", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "FYI", name: "FYI", color: "#22c55e", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "Notification", name: "Notification", color: "#22c55e", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "Mise à jour de réunion", name: "Mise à jour de réunion", color: "#93c5fd", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "Newsletter", name: "Newsletter", color: "#fed7aa", prepareDraft: false, autoReply: false, autoDelete: true },
  { key: "Marketing", name: "Marketing", color: "#fb7185", prepareDraft: false, autoReply: false, autoDelete: true },
  { key: "Traité", name: "Traité", color: "#a78bfa", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "En attente de réponse", name: "En attente de réponse", color: "#facc15", prepareDraft: false, autoReply: false, autoDelete: false },
];

export function getClientSettings(clientId: string): ClientSettings {
  const saved = readSettingsFile(clientId);
  const savedByKey = new Map((saved?.labels || []).map((label) => [label.key, label]));
  return {
    labels: DEFAULT_LABEL_SETTINGS.map((fallback) => sanitizeLabel({ ...fallback, ...savedByKey.get(fallback.key), key: fallback.key }, fallback)),
    updatedAt: saved?.updatedAt || new Date(0).toISOString(),
  };
}

export function saveClientSettings(clientId: string, labels: LabelSetting[]): ClientSettings {
  const fallbackByKey = new Map(DEFAULT_LABEL_SETTINGS.map((label) => [label.key, label]));
  const settings: ClientSettings = {
    labels: labels
      .filter((label) => fallbackByKey.has(label.key))
      .map((label) => sanitizeLabel(label, fallbackByKey.get(label.key)!)),
    updatedAt: new Date().toISOString(),
  };
  fs.mkdirSync(path.dirname(settingsFile(clientId)), { recursive: true });
  fs.writeFileSync(settingsFile(clientId), JSON.stringify(settings, null, 2), "utf-8");
  return settings;
}

function readSettingsFile(clientId: string): ClientSettings | null {
  try {
    return JSON.parse(fs.readFileSync(settingsFile(clientId), "utf-8")) as ClientSettings;
  } catch {
    return null;
  }
}

function settingsFile(clientId: string): string {
  const safeClientId = clientId.replace(/[^a-zA-Z0-9._-]/g, "-");
  return dataPath("client-settings", `${safeClientId}.json`);
}

function sanitizeLabel(label: LabelSetting, fallback: LabelSetting): LabelSetting {
  const name = String(label.name || "").trim().slice(0, 64) || fallback.name;
  const color = /^#[0-9a-fA-F]{6}$/.test(String(label.color || "")) ? label.color : fallback.color;
  return {
    key: fallback.key,
    name,
    color,
    prepareDraft: Boolean(label.prepareDraft),
    autoReply: Boolean(label.autoReply),
    autoDelete: Boolean(label.autoDelete),
  };
}
