import { NextResponse, type NextRequest } from "next/server";

import { currentUser } from "@/lib/auth";
import { setStripeCustomerId } from "@/lib/db";
import {
  checkoutEnabled,
  createCheckoutSession,
  createCustomer,
  priceIdFor,
  siteBaseUrl,
} from "@/lib/stripe";
import { isBillingCycle, isPaidPlan } from "@/lib/stripeCore";

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const plan = String(form.get("plan") || "");
  const cycle = String(form.get("cycle") || "monthly");
  const base = siteBaseUrl(request);

  if (!isPaidPlan(plan) || !isBillingCycle(cycle)) {
    return NextResponse.redirect(`${base}/?billing=plan_inconnu#tarifs`, 303);
  }

  const user = await currentUser();
  // ponytail: the chosen plan is not resumed after login — the dashboard offers
  // the same buttons. Carry it through the session if the drop-off matters.
  if (!user) return NextResponse.redirect(`${base}/connexion`, 303);

  const priceId = checkoutEnabled() ? priceIdFor(plan, cycle) : undefined;
  if (!priceId) {
    return NextResponse.redirect(`${base}/dashboard?billing=indisponible`, 303);
  }

  try {
    let customerId = user.stripeCustomerId;
    if (!customerId) {
      customerId = await createCustomer({ clientId: user.clientId, email: user.email, ownerName: user.ownerName });
      await setStripeCustomerId(user.clientId, customerId);
    }
    const checkoutUrl = await createCheckoutSession({
      customerId,
      priceId,
      clientId: user.clientId,
      successUrl: `${base}/dashboard?billing=succes`,
      cancelUrl: `${base}/dashboard?billing=annule`,
    });
    return NextResponse.redirect(checkoutUrl, 303);
  } catch (error) {
    console.error("Stripe checkout failed", error);
    return NextResponse.redirect(`${base}/dashboard?billing=erreur`, 303);
  }
}
