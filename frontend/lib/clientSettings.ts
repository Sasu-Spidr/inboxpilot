import fs from "node:fs";
import path from "node:path";

import { dataPath } from "./paths";

export type LabelSetting = {
  key: string;
  name: string;
  description: string;
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
  { key: "À traiter", name: "À traiter", description: "Factures, contrats, documents, paiements, accès ou problèmes de compte à gérer manuellement.", color: "#8b8b7a", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "À répondre", name: "À répondre", description: "Messages qui demandent clairement une réponse humaine ou commerciale.", color: "#0d9488", prepareDraft: true, autoReply: false, autoDelete: false },
  { key: "Relance", name: "Relance", description: "Suivis ou rappels demandant de revenir vers une personne.", color: "#f97316", prepareDraft: true, autoReply: false, autoDelete: false },
  { key: "Commentaire", name: "Commentaire", description: "Mentions, avis, remarques ou retours collaboratifs à lire.", color: "#eab308", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "FYI", name: "FYI", description: "Informations utiles à lire ou conserver, sans action immédiate.", color: "#22c55e", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "Notification", name: "Notification", description: "Alertes automatiques liées à un compte, une application, un code ou un service.", color: "#22c55e", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "Mise à jour de réunion", name: "Mise à jour de réunion", description: "Invitations, rappels, acceptations, annulations ou modifications de réunion.", color: "#93c5fd", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "Newsletter", name: "Newsletter", description: "Contenus éditoriaux récurrents : actualités, digest, bulletins ou résumés.", color: "#fed7aa", prepareDraft: false, autoReply: false, autoDelete: true },
  { key: "Marketing", name: "Marketing", description: "Promotions, prospection, publicités, offres commerciales ou messages d'acquisition.", color: "#fb7185", prepareDraft: false, autoReply: false, autoDelete: true },
  { key: "Traité", name: "Traité", description: "Messages déjà résolus, confirmés, terminés ou sans action restante.", color: "#a78bfa", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "En attente de réponse", name: "En attente de réponse", description: "Conversations où une réponse ou confirmation externe est encore attendue.", color: "#facc15", prepareDraft: false, autoReply: false, autoDelete: false },
];

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
  };
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
