import crypto from "node:crypto";

export type SubscriptionTier = "free" | "pro" | "business";
export type BillingCycle = "monthly" | "yearly";
export type PaidPlan = Exclude<SubscriptionTier, "free">;

export type PriceCatalog = Partial<Record<`${PaidPlan}_${BillingCycle}`, string>>;

export const SUBSCRIPTION_STATUSES = [
  "inactive",
  "trialing",
  "active",
  "past_due",
  "unpaid",
  "incomplete",
  "incomplete_expired",
  "paused",
  "canceled",
] as const;

export type SubscriptionStatus = (typeof SUBSCRIPTION_STATUSES)[number];

export function isPaidPlan(value: unknown): value is PaidPlan {
  return value === "pro" || value === "business";
}

export function isBillingCycle(value: unknown): value is BillingCycle {
  return value === "monthly" || value === "yearly";
}

export function normalizeSubscriptionStatus(value: unknown): SubscriptionStatus {
  return SUBSCRIPTION_STATUSES.includes(value as SubscriptionStatus) ? (value as SubscriptionStatus) : "inactive";
}

/** A status that still entitles the account to its paid tier. */
export function isEntitledStatus(status: SubscriptionStatus): boolean {
  return status === "active" || status === "trialing" || status === "past_due";
}

export function tierForPrice(priceId: string, catalog: PriceCatalog): PaidPlan | null {
  for (const [key, value] of Object.entries(catalog)) {
    if (value && value === priceId) return key.split("_")[0] as PaidPlan;
  }
  return null;
}

/**
 * Verify a `Stripe-Signature` header against the raw request body.
 * Mirrors Stripe's documented scheme: HMAC-SHA256 over `<timestamp>.<payload>`,
 * compared in constant time, within a replay tolerance.
 */
export function verifyWebhookSignature(input: {
  payload: string;
  header: string | null;
  secret: string;
  toleranceSeconds?: number;
  nowSeconds?: number;
}): boolean {
  if (!input.header || !input.secret) return false;
  const tolerance = input.toleranceSeconds ?? 300;
  const now = input.nowSeconds ?? Math.floor(Date.now() / 1000);

  const parts = input.header.split(",").map((part) => part.trim());
  const timestamp = Number(parts.find((part) => part.startsWith("t="))?.slice(2));
  if (!Number.isFinite(timestamp) || Math.abs(now - timestamp) > tolerance) return false;

  const expected = crypto
    .createHmac("sha256", input.secret)
    .update(`${timestamp}.${input.payload}`)
    .digest("hex");

  return parts
    .filter((part) => part.startsWith("v1="))
    .map((part) => part.slice(3))
    .some((signature) => {
      if (signature.length !== expected.length) return false;
      return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
    });
}
