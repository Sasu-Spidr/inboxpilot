import type { SubscriptionTier } from "./db";

export type SubscriptionFeature =
  | "automatic_actions"
  | "automatic_drafts"
  | "advanced_rules"
  | "advanced_statistics";

const ENTITLED_STATUSES = new Set(["active", "trialing", "past_due"]);

const MAILBOX_LIMITS: Record<SubscriptionTier, number> = {
  free: 1,
  pro: 3,
  business: 10,
};

export function isEntitledStatus(status: string): boolean {
  return ENTITLED_STATUSES.has(String(status || "").trim().toLowerCase());
}

export function effectiveSubscriptionTier(tier: SubscriptionTier, status: string): SubscriptionTier {
  if (tier === "free") return "free";
  return isEntitledStatus(status) ? tier : "free";
}

export function mailboxLimitFor(tier: SubscriptionTier, status: string): number {
  return MAILBOX_LIMITS[effectiveSubscriptionTier(tier, status)];
}

export function hasSubscriptionFeature(
  tier: SubscriptionTier,
  status: string,
  feature: SubscriptionFeature,
): boolean {
  const effectiveTier = effectiveSubscriptionTier(tier, status);
  if (feature === "automatic_actions" || feature === "automatic_drafts") {
    return effectiveTier === "pro" || effectiveTier === "business";
  }
  return effectiveTier === "business";
}
