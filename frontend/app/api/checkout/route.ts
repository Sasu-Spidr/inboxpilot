import { NextResponse } from "next/server";

import { currentUser } from "@/lib/auth";
import { findUserByClientId, updateStripeCustomer } from "@/lib/db";
import {
  publicFrontendUrl,
  stripeClient,
  stripePriceId,
  type BillingCycle,
  type PaidSubscriptionTier,
} from "@/lib/stripe";

export async function POST(request: Request) {
  const user = await currentUser();
  if (!user) return NextResponse.redirect(`${publicFrontendUrl()}/connexion?error=auth`, 303);

  const selection = await readSelection(request);
  if (!selection) return NextResponse.json({ error: "Invalid subscription selection" }, { status: 400 });

  const row = await findUserByClientId(user.clientId);
  if (!row) return NextResponse.json({ error: "Account not found" }, { status: 404 });
  if (row.stripe_subscription_id && !["canceled", "incomplete_expired"].includes(row.subscription_status)) {
    return NextResponse.json(
      { error: "An active subscription already exists. Use the customer portal to manage it." },
      { status: 409 },
    );
  }

  const stripe = stripeClient();
  let customerId = row.stripe_customer_id;
  if (!customerId) {
    const customer = await stripe.customers.create({
      email: user.email,
      name: user.ownerName,
      metadata: { client_id: user.clientId },
    });
    customerId = customer.id;
    await updateStripeCustomer(user.clientId, customerId);
  }

  const baseUrl = publicFrontendUrl();
  const session = await stripe.checkout.sessions.create({
    mode: "subscription",
    customer: customerId,
    client_reference_id: user.clientId,
    line_items: [{ price: stripePriceId(selection.tier, selection.cycle), quantity: 1 }],
    allow_promotion_codes: true,
    success_url: `${baseUrl}/dashboard?billing=success&session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${baseUrl}/dashboard?billing=canceled`,
    metadata: { client_id: user.clientId, tier: selection.tier, cycle: selection.cycle },
    subscription_data: {
      metadata: { client_id: user.clientId, tier: selection.tier, cycle: selection.cycle },
    },
  });

  if (!session.url) return NextResponse.json({ error: "Stripe did not return a Checkout URL" }, { status: 502 });
  return NextResponse.redirect(session.url, 303);
}

async function readSelection(
  request: Request,
): Promise<{ tier: PaidSubscriptionTier; cycle: BillingCycle } | null> {
  const contentType = request.headers.get("content-type") || "";
  let tier: string;
  let cycle: string;
  if (contentType.includes("application/json")) {
    const payload = (await request.json()) as { tier?: unknown; cycle?: unknown };
    tier = String(payload.tier || "").toLowerCase();
    cycle = String(payload.cycle || "").toLowerCase();
  } else {
    const form = await request.formData();
    tier = String(form.get("tier") || "").toLowerCase();
    cycle = String(form.get("cycle") || "").toLowerCase();
  }
  if (!(["pro", "business"] as string[]).includes(tier)) return null;
  if (!(["monthly", "yearly"] as string[]).includes(cycle)) return null;
  return { tier: tier as PaidSubscriptionTier, cycle: cycle as BillingCycle };
}
