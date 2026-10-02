import { NextResponse } from "next/server";

import { deleteAccountFiles } from "@/lib/accountPrivacy";
import { clearSession, currentUser, verifyPassword } from "@/lib/auth";
import { findUserByClientId, retainBillingRecordAndDeleteUser } from "@/lib/db";
import { stripeClient } from "@/lib/stripe";

export async function POST(request: Request) {
  const user = await currentUser();
  if (!user) return NextResponse.redirect(new URL("/connexion", request.url), 303);
  if (!sameOrigin(request)) return NextResponse.json({ error: "Origine refusée" }, { status: 403 });
  const form = await request.formData();
  const password = String(form.get("password") || "");
  const confirmation = String(form.get("confirmation") || "").trim();
  if (confirmation !== "SUPPRIMER" || !verifyPassword(password, user)) {
    return NextResponse.redirect(new URL("/account/delete-account?error=confirmation", request.url), 303);
  }
  const row = await findUserByClientId(user.clientId);
  if (!row) return NextResponse.redirect(new URL("/connexion", request.url), 303);

  if (row.stripe_subscription_id && !["canceled", "incomplete_expired"].includes(row.subscription_status)) {
    await stripeClient().subscriptions.cancel(row.stripe_subscription_id);
  }
  deleteAccountFiles(row.client_id);
  await retainBillingRecordAndDeleteUser(row);
  await clearSession();
  return NextResponse.redirect(new URL("/connexion?deleted=1", request.url), 303);
}

function sameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  const expectedHost = request.headers.get("x-forwarded-host") || request.headers.get("host");
  try { return new URL(origin).host === expectedHost; } catch { return false; }
}
