import { NextResponse } from "next/server";

import { currentUser } from "@/lib/auth";
import { findUserByClientId } from "@/lib/db";
import { publicFrontendUrl, stripeClient } from "@/lib/stripe";

export async function POST() {
  const user = await currentUser();
  if (!user) return NextResponse.redirect(`${publicFrontendUrl()}/connexion?error=auth`, 303);

  const row = await findUserByClientId(user.clientId);
  if (!row?.stripe_customer_id) {
    return NextResponse.json({ error: "No Stripe customer exists for this account" }, { status: 404 });
  }

  const session = await stripeClient().billingPortal.sessions.create({
    customer: row.stripe_customer_id,
    return_url: `${publicFrontendUrl()}/dashboard`,
  });
  return NextResponse.redirect(session.url, 303);
}
