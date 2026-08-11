import { NextResponse } from "next/server";

import { currentMfaPendingUser, setSession, verifyTotp } from "@/lib/auth";

export async function POST(request: Request) {
  const user = await currentMfaPendingUser();
  if (!user || !user.mfaEnabled || !user.mfaSecret) {
    return redirectTo(request, "/connexion");
  }

  const form = await request.formData();
  const code = String(form.get("code") || "");
  if (!verifyTotp(code, user.mfaSecret)) {
    return redirectTo(request, "/mfa?error=code");
  }

  await setSession(user.clientId);
  return redirectTo(request, "/dashboard");
}

function redirectTo(request: Request, path: string): NextResponse {
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000";
  const proto = request.headers.get("x-forwarded-proto") || (host.startsWith("localhost") ? "http" : "https");
  return NextResponse.redirect(`${proto}://${host}${path}`, 303);
}
