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
  { key: "À traiter", name: "À traiter", description: "Élément important à gérer manuellement : facture, contrat, document, paiement, accès ou problème de compte.", color: "#8b8b7a", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "À répondre", name: "À répondre", description: "Message qui demande clairement une réponse humaine ou une action de réponse commerciale.", color: "#0d9488", prepareDraft: true, autoReply: false, autoDelete: false },
  { key: "Relance", name: "Relance", description: "Suivi ou rappel demandant explicitement de revenir vers une personne ou de confirmer une action.", color: "#f97316", prepareDraft: true, autoReply: false, autoDelete: false },
  { key: "Commentaire", name: "Commentaire", description: "Avis, remarque, mention ou retour collaboratif à lire, sans demande d'action immédiate.", color: "#eab308", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "FYI", name: "FYI", description: "Information utile à conserver ou lire rapidement, sans urgence, réponse attendue ni caractère commercial évident.", color: "#22c55e", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "Notification", name: "Notification", description: "Alerte automatique liée à un compte, une application, un code, la sécurité ou un service.", color: "#22c55e", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "Mise à jour de réunion", name: "Mise à jour de réunion", description: "Invitation, rappel, acceptation, annulation ou modification de réunion, calendrier ou visioconférence.", color: "#93c5fd", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "Newsletter", name: "Newsletter", description: "Contenu éditorial récurrent : actualités, digest, bulletin, résumé hebdomadaire ou mensuel.", color: "#fed7aa", prepareDraft: false, autoReply: false, autoDelete: true },
  { key: "Marketing", name: "Marketing", description: "Prospection, publicité, promotion, offre commerciale, invitation à acheter ou message d'acquisition.", color: "#fb7185", prepareDraft: false, autoReply: false, autoDelete: true },
  { key: "Traité", name: "Traité", description: "Message déjà résolu, confirmé, terminé ou ne nécessitant plus aucune action particulière.", color: "#a78bfa", prepareDraft: false, autoReply: false, autoDelete: false },
  { key: "En attente de réponse", name: "En attente de réponse", description: "Conversation où une réponse, une confirmation ou un retour externe est encore attendu.", color: "#facc15", prepareDraft: false, autoReply: false, autoDelete: false },
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
  const savedByKey = new Map((saved?.labels || []).map((label) => [label.key, label]));
  return {
    labels: DEFAULT_LABEL_SETTINGS.map((fallback) => {
      const savedLabel = savedByKey.get(fallback.key);
      return sanitizeLabel({ ...fallback, ...normalizeLegacyDescription(savedLabel, fallback), key: fallback.key }, fallback);
    }),
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
  const description = String(label.description || "").trim().slice(0, 240) || fallback.description;
  const color = /^#[0-9a-fA-F]{6}$/.test(String(label.color || "")) ? label.color : fallback.color;
  return {
    key: fallback.key,
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
