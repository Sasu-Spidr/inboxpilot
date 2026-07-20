import fs from "node:fs";
import path from "node:path";

import { dataPath } from "./paths";

export type LabelSetting = {
  key: string;
  name: string;
  description: string;
  color: string;
  priority?: number;
  prepareDraft: boolean;
  autoReply: boolean;
  autoDelete: boolean;
};

export type ClientSettings = {
  labels: LabelSetting[];
  updatedAt: string;
};

export const DEFAULT_LABEL_SETTINGS: LabelSetting[] = [
  { key: "À répondre", name: "À répondre", priority: 100, description: "Un humain identifiable attend une réponse écrite : question directe, demande d'info/de devis, rappel ou relance demandant un retour.", color: "#0d9488", prepareDraft: true, autoReply: false, autoDelete: false },
  { key: "À traiter", name: "À traiter", priority: 90, description: "Action manuelle non limitée à une réponse : payer, signer, valider un document, gérer un accès, un compte ou une opération.", color: "#8b8b7a", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "À lire", name: "À lire", priority: 60, description: "Information destinée à un humain, à lire ou conserver, sans action attendue : FYI, mise au courant, commentaire ou mention collaborative.", color: "#3b82f6", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "Notification", name: "Notification", priority: 40, description: "Message généré par une machine : alerte, code, reçu, confirmation transactionnelle, rappel ou événement calendaire sans action manuelle.", color: "#22c55e", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "Commercial", name: "Commercial", priority: 20, description: "Newsletter, promotion, prospection, publicité, offre commerciale ou envoi de masse. Ne supprime jamais par défaut.", color: "#fb7185", prepareDraft: false, autoReply: false, autoDelete: false },
];

const LEGACY_DEFAULT_KEYS = new Set([
  "À traiter",
  "À répondre",
  "Relance",
  "Commentaire",
  "FYI",
  "Notification",
  "Mise à jour de réunion",
  "Newsletter",
  "Marketing",
  "Traité",
  "En attente de réponse",
]);

const LEGACY_DEFAULT_DESCRIPTIONS = new Map<string, string>([
  ["À traiter", "Email important à gérer manuellement."],
  ["À répondre", "Email qui nécessite une réponse."],
  ["Relance", "Email de suivi ou rappel à traiter."],
  ["Commentaire", "Message contenant un avis, une remarque ou une discussion à lire."],
  ["FYI", "Information transmise pour lecture, sans action directe attendue."],
  ["Notification", "Information automatique sans action urgente."],
  ["Mise à jour de réunion", "Invitation, acceptation, annulation ou changement de réunion."],
  ["Newsletter", "Contenu informatif récurrent."],
  ["Marketing", "Offres commerciales, promotions ou prospection."],
  ["Traité", "Email déjà géré ou ne nécessitant plus d'action."],
  ["En attente de réponse", "Conversation en attente d'un retour externe."],
]);

export function getClientSettings(clientId: string): ClientSettings {
  const saved = readSettingsFile(clientId);
  if (saved && Array.isArray(saved.labels) && saved.labels.length > 0) {
    if (isLegacyDefaultSet(saved.labels)) {
      return {
        labels: DEFAULT_LABEL_SETTINGS.map((label) => sanitizeLabel(label, label)),
        updatedAt: saved.updatedAt || new Date(0).toISOString(),
      };
    }
    return {
      labels: sanitizeLabels(saved.labels),
      updatedAt: saved.updatedAt || new Date(0).toISOString(),
    };
  }
  return {
    labels: DEFAULT_LABEL_SETTINGS.map((label) => sanitizeLabel(label, label)),
    updatedAt: new Date(0).toISOString(),
  };
}

export function saveClientSettings(clientId: string, labels: LabelSetting[]): ClientSettings {
  const settings: ClientSettings = {
    labels: sanitizeLabels(labels),
    updatedAt: new Date().toISOString(),
  };
  fs.mkdirSync(path.dirname(settingsFile(clientId)), { recursive: true });
  fs.writeFileSync(settingsFile(clientId), JSON.stringify(settings, null, 2), "utf-8");
  return settings;
}

export function deleteClientSettings(clientId: string): void {
  try {
    fs.unlinkSync(settingsFile(clientId));
  } catch {
    // The user may still be on default settings, so there may be no file to remove.
  }
}

function sanitizeLabels(labels: LabelSetting[]): LabelSetting[] {
  const usedKeys = new Set<string>();
  const fallbackByKey = new Map(DEFAULT_LABEL_SETTINGS.map((label) => [label.key, label]));
  const sanitized: LabelSetting[] = [];

  for (const raw of labels) {
    const fallback = fallbackByKey.get(raw.key) || raw;
    const label = sanitizeLabel(normalizeLegacyDescription(raw, fallback) || raw, fallback);
    if (!label.name) continue;
    const key = uniqueKey(label.key || slugify(label.name), usedKeys);
    sanitized.push({ ...label, key });
  }

  return sanitized;
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
  const description = String(label.description || "").trim().slice(0, 360) || fallback.description || "Libellé personnalisé.";
  const color = /^#[0-9a-fA-F]{6}$/.test(String(label.color || "")) ? label.color : fallback.color || "#14b8a6";
  return {
    key: String(label.key || fallback.key || slugify(name)).trim().slice(0, 80),
    name,
    description,
    color,
    prepareDraft: Boolean(label.prepareDraft),
    autoReply: Boolean(label.autoReply),
    autoDelete: Boolean(label.autoDelete),
    priority: Number.isFinite(Number(label.priority)) ? Number(label.priority) : fallback.priority,
  };
}

function isLegacyDefaultSet(labels: LabelSetting[]): boolean {
  const keys = labels.map((label) => String(label.key || "").trim()).filter(Boolean);
  if (keys.length < 8) return false;
  return keys.every((key) => LEGACY_DEFAULT_KEYS.has(key));
}

function normalizeLegacyDescription(label: LabelSetting | undefined, fallback: LabelSetting): LabelSetting | undefined {
  if (!label) return undefined;
  const legacyDescription = LEGACY_DEFAULT_DESCRIPTIONS.get(fallback.key);
  if (!legacyDescription || String(label.description || "").trim() !== legacyDescription) return label;
  return { ...label, description: fallback.description };
}

function uniqueKey(value: string, usedKeys: Set<string>): string {
  const base = value.trim() || "label";
  let key = base;
  let suffix = 2;
  while (usedKeys.has(key)) {
    key = `${base}-${suffix}`;
    suffix += 1;
  }
  usedKeys.add(key);
  return key;
}

function slugify(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60) || `custom-${Date.now()}`;
}
