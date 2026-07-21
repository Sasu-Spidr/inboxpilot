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
  markAsRead: boolean;
  autoDeleteUnreadAfterDays?: number | null;
};

export type ClientSettings = {
  labels: LabelSetting[];
  updatedAt: string;
};

const CEO_LABEL_DESCRIPTIONS = {
  "À répondre": `Définition. Un humain identifiable attend une réponse écrite de ma part.
Une réponse textuelle réglerait le mail. Inclut les relances (quelqu'un réclame un retour promis). Signaux. Question directe, demande d'info ou de devis, sollicitation commerciale d'un prospect réel, message personnel appelant un retour, rappel dirigé vers moi (« avez-vous eu le temps de… »). Ne pas confondre :
• Facture/contrat/accès où répondre par texte ne suffit pas → À traiter.
• Expéditeur automatique (no-reply) même avec un « confirmez » → Notification.
• Compliment ou mise au courant sans réponse réellement attendue → À lire.
Métadonnée urgence : mets haute si le mail est une relance, mentionne une échéance proche, ou emploie un ton pressant ; sinon normale.`,
  "À traiter": `Définition. Le mail exige une action manuelle qui n'est pas une simple réponse : payer, signer, valider un document, gérer un accès ou un compte, effectuer une opération. Signaux. Facture à régler, contrat à signer, document à valider, demande d'accès légitime, alerte de sécurité exigeant une action réelle. Ne pas confondre :
• Simple question sur un document (« quel est le montant ? ») → À répondre.
• Reçu / confirmation d'une opération déjà faite → Notification.
• Promo urgente déguisée (« dernière chance -50 % ») → Commercial.`,
  "À lire": `Définition. Information destinée à un humain, à lire ou conserver, sans action attendue. Regroupe FYI, mises au courant, commentaires et mentions collaboratifs. Signaux. Transfert « pour info », note interne, mention dans un fil, commentaire sur un document, retour d'un collègue, document partagé sans demande. Ne pas confondre :
• Le message attend un retour de ma part → À répondre.
• Message généré par un système/application → Notification.
• Contenu éditorial d'abonnement ou promotion → Commercial.`,
  Notification: `Définition. Message généré par une machine : alerte, code, confirmation transactionnelle, événement calendaire. Aucune action manuelle requise. Signaux. Expéditeur no-reply / notifications@, code de connexion, alerte système, reçu, invitation ou modification de réunion (fichier .ics), rappel automatique d'événement. Ne pas confondre :
• L'alerte exige une action manuelle réelle (« connexion suspecte, sécurisez votre compte ») → À traiter.
• Message écrit par un humain pour être lu → À lire.
• Promotion ou prospection → Commercial.`,
  Commercial: `Définition. Contenu d'abonnement éditorial, promotion, prospection, publicité, offre commerciale, acquisition. Signaux. Newsletter récurrente, cold email, promo/remise, argumentaire de vente, lien de désabonnement, envoi de masse. Ne pas confondre :
• Mail transactionnel légitime d'un service que j'utilise (reçu, confirmation) → Notification.
• Message personnel ou professionnel individuel → À répondre ou À lire.
• ⚠ Ce libellé peut déclencher une suppression (si l'utilisateur l'a activée). Au moindre doute sur le caractère de masse/commercial, ne choisis pas Commercial → Notification ou À lire.`,
} as const;

export const DEFAULT_LABEL_SETTINGS: LabelSetting[] = [
  { key: "À répondre", name: "À répondre", priority: 100, description: CEO_LABEL_DESCRIPTIONS["À répondre"], color: "#0d9488", prepareDraft: true, autoReply: false, autoDelete: false, markAsRead: false, autoDeleteUnreadAfterDays: null },
  { key: "À traiter", name: "À traiter", priority: 90, description: CEO_LABEL_DESCRIPTIONS["À traiter"], color: "#8b8b7a", prepareDraft: false, autoReply: false, autoDelete: false, markAsRead: false, autoDeleteUnreadAfterDays: null },
  { key: "À lire", name: "À lire", priority: 60, description: CEO_LABEL_DESCRIPTIONS["À lire"], color: "#3b82f6", prepareDraft: false, autoReply: false, autoDelete: false, markAsRead: false, autoDeleteUnreadAfterDays: null },
  { key: "Notification", name: "Notification", priority: 40, description: CEO_LABEL_DESCRIPTIONS.Notification, color: "#22c55e", prepareDraft: false, autoReply: false, autoDelete: false, markAsRead: false, autoDeleteUnreadAfterDays: null },
  { key: "Commercial", name: "Commercial", priority: 20, description: CEO_LABEL_DESCRIPTIONS.Commercial, color: "#fb7185", prepareDraft: false, autoReply: false, autoDelete: false, markAsRead: false, autoDeleteUnreadAfterDays: null },
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

const LEGACY_DEFAULT_DESCRIPTIONS: Array<[string, string]> = [
  ["À traiter", "Email important à gérer manuellement."],
  ["À traiter", "Action manuelle non limitée à une réponse."],
  ["À traiter", "Action manuelle non limitée à une réponse : payer, signer, valider un document, gérer un accès, un compte ou une opération."],
  ["À répondre", "Email qui nécessite une réponse."],
  ["À répondre", "Un humain identifiable attend une réponse écrite."],
  ["À répondre", "Un humain identifiable attend une réponse écrite : question directe, demande d'info/de devis, rappel ou relance demandant un retour."],
  ["À lire", "Information destinée à un humain, à lire ou conserver."],
  ["À lire", "Information destinée à un humain, à lire ou conserver, sans action attendue : FYI, mise au courant, commentaire ou mention collaborative."],
  ["Notification", "Message généré par une machine, sans action manuelle."],
  ["Notification", "Message généré par une machine : alerte, code, reçu, confirmation transactionnelle, rappel ou événement calendaire sans action manuelle."],
  ["Commercial", "Newsletter, promotion, prospection ou offre commerciale."],
  ["Commercial", "Newsletter, promotion, prospection, publicité, offre commerciale ou envoi de masse. Ne supprime jamais par défaut."],
  ["Relance", "Email de suivi ou rappel à traiter."],
  ["Commentaire", "Message contenant un avis, une remarque ou une discussion à lire."],
  ["FYI", "Information transmise pour lecture, sans action directe attendue."],
  ["Notification", "Information automatique sans action urgente."],
  ["Mise à jour de réunion", "Invitation, acceptation, annulation ou changement de réunion."],
  ["Newsletter", "Contenu informatif récurrent."],
  ["Marketing", "Offres commerciales, promotions ou prospection."],
  ["Traité", "Email déjà géré ou ne nécessitant plus d'action."],
  ["En attente de réponse", "Conversation en attente d'un retour externe."],
];

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
  const description = String(label.description || "").trim().slice(0, 2000) || fallback.description || "Libellé personnalisé.";
  const color = /^#[0-9a-fA-F]{6}$/.test(String(label.color || "")) ? label.color : fallback.color || "#14b8a6";
  return {
    key: String(label.key || fallback.key || slugify(name)).trim().slice(0, 80),
    name,
    description,
    color,
    prepareDraft: Boolean(label.prepareDraft),
    autoReply: Boolean(label.autoReply),
    autoDelete: Boolean(label.autoDelete),
    markAsRead: Boolean(label.markAsRead),
    autoDeleteUnreadAfterDays: sanitizeUnreadDeleteDays(label.autoDeleteUnreadAfterDays),
    priority: Number.isFinite(Number(label.priority)) ? Number(label.priority) : fallback.priority,
  };
}

function sanitizeUnreadDeleteDays(value: unknown): number | null {
  const days = Number(value);
  if (!Number.isFinite(days) || days <= 0) return null;
  return Math.min(365, Math.max(1, Math.floor(days)));
}

function isLegacyDefaultSet(labels: LabelSetting[]): boolean {
  const keys = labels.map((label) => String(label.key || "").trim()).filter(Boolean);
  if (keys.length < 8) return false;
  return keys.every((key) => LEGACY_DEFAULT_KEYS.has(key));
}

function normalizeLegacyDescription(label: LabelSetting | undefined, fallback: LabelSetting): LabelSetting | undefined {
  if (!label) return undefined;
  const description = String(label.description || "").trim();
  const isLegacyDescription = LEGACY_DEFAULT_DESCRIPTIONS.some(
    ([key, legacyDescription]) => key === fallback.key && description === legacyDescription,
  );
  if (!isLegacyDescription) return label;
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
