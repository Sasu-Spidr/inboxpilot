import { NextResponse, type NextRequest } from "next/server";

import {
  applySubscriptionState,
  findUserByClientId,
  findUserByStripeCustomerId,
  logSecurityEvent,
  setStripeCustomerId,
  updateSubscriptionStatus,
} from "@/lib/db";
import { planForPrice, verifyStripeSignature } from "@/lib/stripe";
import { isEntitledStatus, normalizeSubscriptionStatus, type SubscriptionTier } from "@/lib/stripeCore";

export const dynamic = "force-dynamic";

type StripeRef = string | { id?: string } | null | undefined;

type StripeEvent = {
  type: string;
  data: {
    object: {
      id?: string;
      customer?: StripeRef;
      status?: string;
      metadata?: { client_id?: string };
      items?: { data?: { price?: { id?: string } }[] };
    };
  };
};

export async function POST(request: NextRequest) {
  const payload = await request.text();

  if (!verifyStripeSignature(payload, request.headers.get("stripe-signature"))) {
    await logSecurityEvent({
      eventType: "stripe_webhook_signature_rejected",
      ip: request.headers.get("x-forwarded-for"),
      userAgent: request.headers.get("user-agent"),
    });
    return NextResponse.json({ error: "invalid_signature" }, { status: 400 });
  }

  let event: StripeEvent;
  try {
    event = JSON.parse(payload) as StripeEvent;
  } catch {
    return NextResponse.json({ error: "invalid_payload" }, { status: 400 });
  }

  try {
    await handleEvent(event);
  } catch (error) {
    // 500 makes Stripe retry, which is what we want for a transient DB failure.
    console.error("Stripe webhook handling failed", event.type, error);
    return NextResponse.json({ error: "handler_failed" }, { status: 500 });
  }

  return NextResponse.json({ received: true });
}

async function handleEvent(event: StripeEvent): Promise<void> {
  const object = event.data?.object || {};

  switch (event.type) {
    case "customer.subscription.created":
    case "customer.subscription.updated":
    case "customer.subscription.deleted": {
      const clientId = await resolveClientId(object.customer, object.metadata?.client_id);
      if (!clientId) return;
      const deleted = event.type === "customer.subscription.deleted";
      const status = deleted ? "canceled" : normalizeSubscriptionStatus(object.status);
      const priceId = object.items?.data?.[0]?.price?.id;
      const plan = priceId ? planForPrice(priceId) : null;
      const tier: SubscriptionTier = deleted || !isEntitledStatus(status) || !plan ? "free" : plan;
      await applySubscriptionState({
        clientId,
        tier,
        status,
        stripeSubscriptionId: deleted ? null : object.id || null,
      });
      return;
    }
    // Only failures are acted on here: `customer.subscription.updated` carries the
    // authoritative status on every recovery, and a trial's 0 EUR invoice succeeds
    // immediately, which would otherwise overwrite `trialing` with `active`.
    case "invoice.payment_failed": {
      const clientId = await resolveClientId(object.customer, object.metadata?.client_id);
      if (!clientId) return;
      await updateSubscriptionStatus(clientId, "past_due");
      return;
    }
    default:
      return;
  }
}

async function resolveClientId(customer: StripeRef, metadataClientId?: string): Promise<string | null> {
  const customerId = typeof customer === "string" ? customer : customer?.id;
  if (customerId) {
    const known = await findUserByStripeCustomerId(customerId);
    if (known) return known.client_id;
  }
  if (!metadataClientId) return null;
  const user = await findUserByClientId(metadataClientId);
  if (!user) return null;
  if (customerId) await setStripeCustomerId(user.client_id, customerId);
  return user.client_id;
}
