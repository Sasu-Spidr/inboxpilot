import { NextResponse } from "next/server";

import { currentUser, encryptMfaSecret, verifyTotp } from "@/lib/auth";
import { updateUserMfa } from "@/lib/db";
import { mfaFeatureEnabled } from "@/lib/features";

export async function POST(request: Request) {
  if (!mfaFeatureEnabled()) return redirectTo(request, "/settings");
  const user = await currentUser();
  if (!user) return redirectTo(request, "/connexion");

  const form = await request.formData();
  const secret = String(form.get("secret") || "").replace(/\s+/g, "");
  const code = String(form.get("code") || "");

  if (!secret || !verifyTotp(code, secret)) {
    return redirectTo(request, "/mfa/setup?error=code");
  }

  await updateUserMfa(user.clientId, { enabled: true, secret: encryptMfaSecret(secret) });
  return redirectTo(request, "/settings?mfa=enabled");
}

function redirectTo(request: Request, path: string): NextResponse {
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000";
  const proto = request.headers.get("x-forwarded-proto") || (host.startsWith("localhost") ? "http" : "https");
  return NextResponse.redirect(`${proto}://${host}${path}`, 303);
}
