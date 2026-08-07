export const ALLOWED_LABELS = ["À répondre", "À traiter", "À lire", "Notification", "Commercial"] as const;

export function canonicalLabelKey(label: string): string {
  return String(label || "").trim();
}
