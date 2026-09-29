import { NextResponse, type NextRequest } from "next/server";

import { currentUser } from "@/lib/auth";
import { checkoutEnabled, createPortalSession, siteBaseUrl } from "@/lib/stripe";

export async function POST(request: NextRequest) {
  const base = siteBaseUrl(request);
  const user = await currentUser();
  if (!user) return NextResponse.redirect(`${base}/connexion`, 303);
  if (!checkoutEnabled() || !user.stripeCustomerId) {
    return NextResponse.redirect(`${base}/dashboard?billing=indisponible`, 303);
  }

  try {
    const portalUrl = await createPortalSession({
      customerId: user.stripeCustomerId,
      returnUrl: `${base}/dashboard`,
    });
    return NextResponse.redirect(portalUrl, 303);
  } catch (error) {
    console.error("Stripe customer portal failed", error);
    return NextResponse.redirect(`${base}/dashboard?billing=erreur`, 303);
  }
}
