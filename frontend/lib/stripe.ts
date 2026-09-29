import { optionalSecret, secret } from "./baoSecrets";
import {
  type BillingCycle,
  type PaidPlan,
  type PriceCatalog,
  tierForPrice,
  verifyWebhookSignature,
} from "./stripeCore";

const STRIPE_API_BASE = "https://api.stripe.com/v1";
const STRIPE_API_VERSION = "2024-06-20";

/** Free trial granted on every new paid subscription; `trialing` already entitles the tier. */
const TRIAL_PERIOD_DAYS = 14;

export function priceCatalog(): PriceCatalog {
  return {
    pro_monthly: process.env.STRIPE_PRICE_PRO_MONTHLY || undefined,
    pro_yearly: process.env.STRIPE_PRICE_PRO_YEARLY || undefined,
    business_monthly: process.env.STRIPE_PRICE_BUSINESS_MONTHLY || undefined,
    business_yearly: process.env.STRIPE_PRICE_BUSINESS_YEARLY || undefined,
  };
}

export function priceIdFor(plan: PaidPlan, cycle: BillingCycle): string | undefined {
  return priceCatalog()[`${plan}_${cycle}`];
}

/** Checkout and the customer portal need the API key; the webhook needs its own secret. */
export function checkoutEnabled(): boolean {
  return Boolean(optionalSecret("STRIPE_SECRET_KEY")) && Object.values(priceCatalog()).some(Boolean);
}

export function planForPrice(priceId: string): PaidPlan | null {
  return tierForPrice(priceId, priceCatalog());
}

export function verifyStripeSignature(payload: string, header: string | null): boolean {
  const webhookSecret = optionalSecret("STRIPE_WEBHOOK_SECRET");
  if (!webhookSecret) return false;
  return verifyWebhookSignature({ payload, header, secret: webhookSecret });
}

export async function stripeRequest<T>(path: string, params?: Record<string, string>): Promise<T> {
  const response = await fetch(`${STRIPE_API_BASE}/${path}`, {
    method: params ? "POST" : "GET",
    headers: {
      Authorization: `Bearer ${secret("STRIPE_SECRET_KEY")}`,
      "Stripe-Version": STRIPE_API_VERSION,
      ...(params ? { "Content-Type": "application/x-www-form-urlencoded" } : {}),
    },
    body: params ? new URLSearchParams(params).toString() : undefined,
    cache: "no-store",
    signal: AbortSignal.timeout(15_000),
  });
  const payload = (await response.json()) as T & { error?: { message?: string } };
  if (!response.ok) {
    throw new Error(`Stripe ${path} failed with HTTP ${response.status}: ${payload?.error?.message || "unknown error"}`);
  }
  return payload;
}

export async function createCustomer(input: { clientId: string; email: string; ownerName: string }): Promise<string> {
  const customer = await stripeRequest<{ id: string }>("customers", {
    email: input.email,
    name: input.ownerName,
    "metadata[client_id]": input.clientId,
  });
  return customer.id;
}

export async function createCheckoutSession(input: {
  customerId: string;
  priceId: string;
  clientId: string;
  successUrl: string;
  cancelUrl: string;
}): Promise<string> {
  const session = await stripeRequest<{ url: string | null }>("checkout/sessions", {
    mode: "subscription",
    customer: input.customerId,
    client_reference_id: input.clientId,
    "line_items[0][price]": input.priceId,
    "line_items[0][quantity]": "1",
    "subscription_data[metadata][client_id]": input.clientId,
    "subscription_data[trial_period_days]": String(TRIAL_PERIOD_DAYS),
    // Prices are tax-exclusive (HT); Stripe Tax computes VAT and needs a billable address.
    "automatic_tax[enabled]": "true",
    "customer_update[address]": "auto",
    "tax_id_collection[enabled]": "true",
    success_url: input.successUrl,
    cancel_url: input.cancelUrl,
  });
  if (!session.url) throw new Error("Stripe returned a checkout session without a URL");
  return session.url;
}

export async function createPortalSession(input: { customerId: string; returnUrl: string }): Promise<string> {
  const session = await stripeRequest<{ url: string | null }>("billing_portal/sessions", {
    customer: input.customerId,
    return_url: input.returnUrl,
  });
  if (!session.url) throw new Error("Stripe returned a portal session without a URL");
  return session.url;
}

export function siteBaseUrl(request: Request): string {
  const configured = process.env.FRONTEND_BASE_URL;
  if (configured) return configured.replace(/\/+$/, "");
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000";
  const proto = request.headers.get("x-forwarded-proto") || (host.startsWith("localhost") ? "http" : "https");
  return `${proto}://${host}`;
}
