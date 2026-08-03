export const ALLOWED_LABELS = ["À répondre", "À traiter", "À lire", "Notification", "Commercial"] as const;

const LABEL_ALIASES = new Map([
  ["A répondre", "À répondre"],
  ["Relance", "À répondre"],
  ["A traiter", "À traiter"],
  ["FYI", "À lire"],
  ["Commentaire", "À lire"],
  ["Newsletter", "À lire"],
  ["Traité", "À lire"],
  ["Traite", "À lire"],
  ["En attente de réponse", "À lire"],
  ["En attente de reponse", "À lire"],
  ["Mise à jour de réunion", "Notification"],
  ["Mise a jour de reunion", "Notification"],
  ["Marketing", "Commercial"],
]);

export function canonicalLabelKey(label: string): string {
  const trimmed = String(label || "").trim();
  return LABEL_ALIASES.get(trimmed) || trimmed;
}
