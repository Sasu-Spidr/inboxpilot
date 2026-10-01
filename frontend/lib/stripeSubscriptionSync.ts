import Stripe from "stripe";

import { findUserByStripeCustomerId, updateSubscription } from "./db";
import { stripeClient, stripeObjectId, subscriptionTierForPrice } from "./stripe";

export async function reconcileCheckoutSession(clientId: string, sessionId: string): Promise<void> {
  const session = await stripeClient().checkout.sessions.retrieve(sessionId, {
    expand: ["subscription"],
  });
  await synchronizeCheckoutSession(session, clientId);
}

export async function reconcileStripeCustomerSubscription(clientId: string, customerId: string): Promise<boolean> {
  const subscriptions = await stripeClient().subscriptions.list({
    customer: customerId,
    status: "all",
    limit: 10,
  });
  const subscription = subscriptions.data.find(
    (candidate) => !["canceled", "incomplete_expired"].includes(candidate.status),
  );
  if (!subscription) return false;
  await synchronizeStripeSubscription(subscription, clientId);
  return true;
}

export async function synchronizeCheckoutSession(
  session: Stripe.Checkout.Session,
  expectedClientId?: string,
): Promise<void> {
  if (session.mode !== "subscription" || session.status !== "complete") {
    throw new Error(`Stripe Checkout session ${session.id} is not a completed subscription`);
  }

  const customerId = stripeObjectId(session.customer);
  const existingUser = customerId ? await findUserByStripeCustomerId(customerId) : null;
  const clientId = session.client_reference_id || session.metadata?.client_id || existingUser?.client_id;
  if (!clientId) throw new Error(`No InboxPilot account matches Stripe Checkout session ${session.id}`);
  if (expectedClientId && clientId !== expectedClientId) {
    throw new Error(`Stripe Checkout session ${session.id} does not belong to the authenticated account`);
  }
  if (existingUser && existingUser.client_id !== clientId) {
    throw new Error(`Stripe customer from Checkout session ${session.id} belongs to another account`);
  }

  const subscription = await checkoutSubscription(session);
  await synchronizeStripeSubscription(subscription, clientId);
}

export async function synchronizeStripeSubscription(
  subscription: Stripe.Subscription,
  expectedClientId?: string,
): Promise<void> {
  const customerId = stripeObjectId(subscription.customer);
  const existingUser = customerId ? await findUserByStripeCustomerId(customerId) : null;
  const clientId = subscription.metadata.client_id || existingUser?.client_id;
  if (!clientId) throw new Error(`No InboxPilot account matches Stripe subscription ${subscription.id}`);
  if (expectedClientId && clientId !== expectedClientId) {
    throw new Error(`Stripe subscription ${subscription.id} does not belong to the authenticated account`);
  }
  if (existingUser && existingUser.client_id !== clientId) {
    throw new Error(`Stripe customer from subscription ${subscription.id} belongs to another account`);
  }

  const subscriptionClientId = subscription.metadata.client_id;
  if (subscriptionClientId && subscriptionClientId !== clientId) {
    throw new Error(`Stripe subscription ${subscription.id} belongs to another account`);
  }
  const priceId = subscription.items.data[0]?.price.id;
  if (!priceId) throw new Error(`Stripe subscription ${subscription.id} has no price`);

  await updateSubscription({
    clientId,
    tier: subscriptionTierForPrice(priceId),
    status: subscription.status,
    customerId,
    subscriptionId: subscription.id,
  });
}

async function checkoutSubscription(session: Stripe.Checkout.Session): Promise<Stripe.Subscription> {
  if (!session.subscription) throw new Error(`Stripe Checkout session ${session.id} has no subscription`);
  if (typeof session.subscription !== "string") return session.subscription;
  return stripeClient().subscriptions.retrieve(session.subscription);
}
