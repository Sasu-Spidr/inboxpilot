import { NextResponse } from "next/server";

import { clientIdFromEmail, createPasswordHash, setSession } from "@/lib/auth";
import {
  checkSignupAbuse,
  clientIp,
  normalizeEmail,
  sleep,
  verifyTurnstileIfConfigured,
} from "@/lib/antiAbuse";
import { createUser, findUserByEmail, logSecurityEvent, touchLastLogin } from "@/lib/db";
import { publicEntryPath, publicSignupEnabled } from "@/lib/features";
import { checkRateLimit, rateLimitKey } from "@/lib/rateLimit";

export async function POST(request: Request) {
  if (!publicSignupEnabled()) {
    await logSecurityEvent({
      eventType: "signup_blocked_public_disabled",
      ip: clientIp(request),
      userAgent: request.headers.get("user-agent"),
      metadata: { path: new URL(request.url).pathname },
    });
    return redirectTo(request, `${publicEntryPath()}?error=signup-disabled`);
  }

  const form = await request.formData();
  const ownerName = String(form.get("ownerName") || "").trim();
  const email = normalizeEmail(String(form.get("email") || ""));
  const password = String(form.get("password") || "");
  const honeypot = String(form.get("companyWebsite") || "");
  const startedAt = String(form.get("signupStartedAt") || "");
  const accessCode = String(form.get("signupAccessCode") || "");
  const turnstileToken = String(form.get("cf-turnstile-response") || "");
  const clientId = clientIdFromEmail(email);
  const limit = checkRateLimit({
    bucket: "register",
    key: rateLimitKey(clientIp(request), email),
    limit: registerRateLimit(),
    windowMs: 60 * 60 * 1000,
  });

  if (!limit.allowed) {
    await logSecurityEvent({
      eventType: "signup_rate_limited",
      email,
      ip: clientIp(request),
      userAgent: request.headers.get("user-agent"),
      metadata: { resetAt: new Date(limit.resetAt).toISOString() },
    });
    return redirectTo(request, `${publicEntryPath()}?error=register`);
  }

  const abuse = checkSignupAbuse({
    ownerName,
    email,
    honeypot,
    startedAt,
    accessCode,
    userAgent: request.headers.get("user-agent"),
  });
  if (!abuse.allowed) {
    await sleep(900);
    await logSecurityEvent({
      eventType: "signup_blocked_abuse",
      email,
      ip: clientIp(request),
      userAgent: request.headers.get("user-agent"),
      metadata: { reason: abuse.reason },
    });
    return redirectTo(request, `${publicEntryPath()}?error=register`);
  }

  const turnstile = await verifyTurnstileIfConfigured({
    token: turnstileToken,
    ip: clientIp(request),
  });
  if (!turnstile.allowed) {
    await sleep(900);
    await logSecurityEvent({
      eventType: "signup_blocked_turnstile",
      email,
      ip: clientIp(request),
      userAgent: request.headers.get("user-agent"),
      metadata: { reason: turnstile.reason },
    });
    return redirectTo(request, `${publicEntryPath()}?error=register`);
  }

  if (!ownerName || !email || !password || password.length < 8) {
    await logSecurityEvent({
      eventType: "signup_invalid",
      email,
      ip: clientIp(request),
      userAgent: request.headers.get("user-agent"),
      metadata: { reason: "invalid_form" },
    });
    return redirectTo(request, `${publicEntryPath()}?error=register`);
  }

  if (await findUserByEmail(email)) {
    await logSecurityEvent({
      eventType: "signup_existing_email",
      email,
      ip: clientIp(request),
      userAgent: request.headers.get("user-agent"),
    });
    return redirectTo(request, `${publicEntryPath()}?error=exists`);
  }

  const { hash, salt } = createPasswordHash(password);
  await createUser({
    clientId,
    ownerName,
    email,
    status: "ACTIVE",
    emailVerified: true,
    passwordHash: hash,
    passwordSalt: salt,
  });
  await setSession(clientId);
  await touchLastLogin(clientId);
  await logSecurityEvent({
    eventType: "signup_success",
    clientId,
    email,
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

function registerRateLimit(): number {
  const value = Number(process.env.REGISTER_RATE_LIMIT_1H || 3);
  return Number.isFinite(value) && value > 0 ? value : 3;
}

export const dynamic = "force-dynamic";
