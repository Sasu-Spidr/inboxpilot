import { NextResponse } from "next/server";

import { currentUser, verifyTotp } from "@/lib/auth";
import { updateUserMfa } from "@/lib/db";
import { mfaFeatureEnabled } from "@/lib/features";

export async function POST(request: Request) {
  if (!mfaFeatureEnabled()) return redirectTo(request, "/settings");
  const user = await currentUser();
  if (!user) return redirectTo(request, "/connexion");

  const form = await request.formData();
  const code = String(form.get("code") || "");
  if (user.mfaEnabled && user.mfaSecret && !verifyTotp(code, user.mfaSecret)) {
    return redirectTo(request, "/settings?mfa=disable-error");
  }

  await updateUserMfa(user.clientId, { enabled: false, secret: null });
  return redirectTo(request, "/settings?mfa=disabled");
}

function redirectTo(request: Request, path: string): NextResponse {
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000";
  const proto = request.headers.get("x-forwarded-proto") || (host.startsWith("localhost") ? "http" : "https");
  return NextResponse.redirect(`${proto}://${host}${path}`, 303);
}
