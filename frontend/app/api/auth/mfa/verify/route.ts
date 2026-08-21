import { NextResponse } from "next/server";

import { currentMfaPendingUser, setSession, verifyTotp } from "@/lib/auth";
import { logSecurityEvent, touchLastLogin } from "@/lib/db";
import { mfaFeatureEnabled } from "@/lib/features";

export async function POST(request: Request) {
  if (!mfaFeatureEnabled()) return redirectTo(request, "/connexion");
  const user = await currentMfaPendingUser();
  if (!user || !user.mfaEnabled || !user.mfaSecret) {
    return redirectTo(request, "/connexion");
  }

  const form = await request.formData();
  const code = String(form.get("code") || "");
  if (!verifyTotp(code, user.mfaSecret)) {
    await logSecurityEvent({
      eventType: "mfa_failed",
      clientId: user.clientId,
      email: user.email,
      ip: clientIp(request),
      userAgent: request.headers.get("user-agent"),
    });
    return redirectTo(request, "/mfa?error=code");
  }

  await setSession(user.clientId);
  await touchLastLogin(user.clientId);
  await logSecurityEvent({
    eventType: "mfa_success",
    clientId: user.clientId,
    email: user.email,
    ip: clientIp(request),
    userAgent: request.headers.get("user-agent"),
  });
  return redirectTo(request, "/dashboard");
}

function redirectTo(request: Request, path: string): NextResponse {
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000";
  const proto = request.headers.get("x-forwarded-proto") || (host.startsWith("localhost") ? "http" : "https");
  return NextResponse.redirect(`${proto}://${host}${path}`, 303);
}

function clientIp(request: Request): string {
  return request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || request.headers.get("x-real-ip") || "";
}
