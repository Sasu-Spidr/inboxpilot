import Stripe from "stripe";
import { NextResponse } from "next/server";

import {
  findUserByStripeCustomerId,
  findUserByStripeSubscriptionId,
  updateSubscription,
  updateSubscriptionStatusByStripeReference,
} from "@/lib/db";
import {
  stripeClient,
  stripeObjectId,
  stripeWebhookSecret,
  subscriptionIdFromInvoice,
} from "@/lib/stripe";
import { synchronizeCheckoutSession, synchronizeStripeSubscription } from "@/lib/stripeSubscriptionSync";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const signature = request.headers.get("stripe-signature");
  if (!signature) return NextResponse.json({ error: "Missing Stripe signature" }, { status: 400 });

  const rawBody = await request.text();
  let event: Stripe.Event;
  try {
    event = stripeClient().webhooks.constructEvent(rawBody, signature, stripeWebhookSecret());
  } catch {
    return NextResponse.json({ error: "Invalid Stripe signature" }, { status: 400 });
  }

  try {
    switch (event.type) {
      case "checkout.session.completed":
        await synchronizeCheckoutSession(event.data.object);
        break;
      case "customer.subscription.created":
      case "customer.subscription.updated":
        await synchronizeStripeSubscription(event.data.object);
        break;
      case "customer.subscription.deleted":
        await cancelSubscription(event.data.object);
        break;
      case "invoice.payment_succeeded":
        await synchronizeInvoiceStatus(event.data.object, "active");
        break;
      case "invoice.payment_failed":
        await synchronizeInvoiceStatus(event.data.object, "past_due");
        break;
      default:
        break;
    }
  } catch (error) {
    console.error("Stripe webhook processing failed", {
      eventId: event.id,
      eventType: event.type,
      error: error instanceof Error ? error.message : String(error),
    });
    return NextResponse.json({ error: "Stripe event processing failed" }, { status: 500 });
  }

  return NextResponse.json({ received: true });
}

async function cancelSubscription(subscription: Stripe.Subscription): Promise<void> {
  const customerId = stripeObjectId(subscription.customer);
  const row =
    (await findUserByStripeSubscriptionId(subscription.id)) ||
    (customerId ? await findUserByStripeCustomerId(customerId) : null);
  const clientId = subscription.metadata.client_id || row?.client_id;
  if (!clientId) throw new Error(`No InboxPilot account matches canceled Stripe subscription ${subscription.id}`);
  await updateSubscription({
    clientId,
    tier: "free",
    status: "canceled",
    customerId,
    subscriptionId: null,
  });
}

async function synchronizeInvoiceStatus(invoice: Stripe.Invoice, status: "active" | "past_due"): Promise<void> {
  await updateSubscriptionStatusByStripeReference({
    customerId: stripeObjectId(invoice.customer),
    subscriptionId: subscriptionIdFromInvoice(invoice),
    status,
  });
}
