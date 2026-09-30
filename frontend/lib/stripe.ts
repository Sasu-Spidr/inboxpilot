import Stripe from "stripe";

import { secret } from "./baoSecrets";
import type { SubscriptionTier } from "./db";

export type BillingCycle = "monthly" | "yearly";
export type PaidSubscriptionTier = Exclude<SubscriptionTier, "free">;

let client: Stripe | null = null;

export function stripeClient(): Stripe {
  if (!client) {
    client = new Stripe(secret("STRIPE_SECRET_KEY"), {
      appInfo: { name: "InboxPilot" },
      maxNetworkRetries: 2,
    });
  }
  return client;
}

export function stripeWebhookSecret(): string {
  return secret("STRIPE_WEBHOOK_SECRET");
}

export function stripePriceId(tier: PaidSubscriptionTier, cycle: BillingCycle): string {
  const name = `STRIPE_PRICE_${tier.toUpperCase()}_${cycle.toUpperCase()}`;
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing required Stripe price variable: ${name}`);
  return value;
}

export function subscriptionTierForPrice(priceId: string): PaidSubscriptionTier {
  for (const tier of ["pro", "business"] as const) {
    for (const cycle of ["monthly", "yearly"] as const) {
      if (stripePriceId(tier, cycle) === priceId) return tier;
    }
  }
  throw new Error(`Stripe price is not configured for InboxPilot: ${priceId}`);
}

export function publicFrontendUrl(): string {
  const value = process.env.FRONTEND_BASE_URL?.trim().replace(/\/+$/, "");
  if (!value) throw new Error("FRONTEND_BASE_URL is required for Stripe redirects");
  return value;
}

export function stripeObjectId(value: string | { id: string } | null | undefined): string | null {
  if (!value) return null;
  return typeof value === "string" ? value : value.id;
}

export function subscriptionIdFromInvoice(invoice: Stripe.Invoice): string | null {
  const raw = invoice as unknown as {
    subscription?: string | { id: string } | null;
    parent?: {
      subscription_details?: {
        subscription?: string | { id: string } | null;
      } | null;
    } | null;
  };
  return stripeObjectId(raw.subscription || raw.parent?.subscription_details?.subscription);
}
