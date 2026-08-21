import { NextResponse } from "next/server";

import { isAccountUsable, setMfaPending, setSession, toUser, verifyPassword } from "@/lib/auth";
import { findUserByEmail, logSecurityEvent, touchLastLogin } from "@/lib/db";
import { mfaFeatureEnabled, publicEntryPath } from "@/lib/features";
import { checkRateLimit, rateLimitKey } from "@/lib/rateLimit";

export async function POST(request: Request) {
  const form = await request.formData();
  const email = String(form.get("email") || "").trim().toLowerCase();
  const password = String(form.get("password") || "");
  const limit = checkRateLimit({
    bucket: "login",
    key: rateLimitKey(clientIp(request), email),
    limit: loginRateLimit(),
    windowMs: 15 * 60 * 1000,
  });

  if (!limit.allowed) {
    await logSecurityEvent({
      eventType: "login_rate_limited",
      email,
      ip: clientIp(request),
      userAgent: request.headers.get("user-agent"),
      metadata: { resetAt: new Date(limit.resetAt).toISOString() },
    });
    return redirectTo(request, `${publicEntryPath()}?error=login`);
  }

  const row = await findUserByEmail(email);
  const user = row ? toUser(row) : null;

  if (!user || !verifyPassword(password, user)) {
    await logSecurityEvent({
      eventType: "login_failed",
      email,
      ip: clientIp(request),
      userAgent: request.headers.get("user-agent"),
      metadata: { reason: "invalid_credentials" },
    });
    return redirectTo(request, `${publicEntryPath()}?error=login`);
  }

  if (!isAccountUsable(user)) {
    await logSecurityEvent({
      eventType: "login_blocked_account_status",
      clientId: user.clientId,
      email: user.email,
      ip: clientIp(request),
      userAgent: request.headers.get("user-agent"),
      metadata: { status: user.status, emailVerified: user.emailVerified },
    });
    return redirectTo(request, `${publicEntryPath()}?error=account`);
  }

  if (mfaFeatureEnabled() && user.mfaEnabled) {
    await setMfaPending(user.clientId);
    await logSecurityEvent({
      eventType: "login_mfa_required",
      clientId: user.clientId,
      email: user.email,
      ip: clientIp(request),
      userAgent: request.headers.get("user-agent"),
    });
    return redirectTo(request, "/mfa");
  }

  await setSession(user.clientId);
  await touchLastLogin(user.clientId);
  await logSecurityEvent({
    eventType: "login_success",
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

function loginRateLimit(): number {
  const value = Number(process.env.LOGIN_RATE_LIMIT_15M || 10);
  return Number.isFinite(value) && value > 0 ? value : 10;
}
