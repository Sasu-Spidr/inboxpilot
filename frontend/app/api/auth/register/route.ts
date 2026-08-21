import { NextResponse } from "next/server";
import crypto from "node:crypto";

import { clientIdFromEmail, createPasswordHash } from "@/lib/auth";
import { createEmailVerificationToken, createUser, findUserByEmail, logSecurityEvent } from "@/lib/db";
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
  const email = String(form.get("email") || "").trim().toLowerCase();
  const password = String(form.get("password") || "");
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
    status: "PENDING_EMAIL_VERIFICATION",
    emailVerified: false,
    passwordHash: hash,
    passwordSalt: salt,
  });
  const token = crypto.randomBytes(32).toString("base64url");
  await createEmailVerificationToken({
    id: crypto.randomUUID(),
    clientId,
    tokenHash: verificationTokenHash(token),
    expiresAt: new Date(Date.now() + emailVerificationTtlMinutes() * 60 * 1000),
  });
  await logSecurityEvent({
    eventType: "signup_pending_email_verification",
    clientId,
    email,
    ip: clientIp(request),
    userAgent: request.headers.get("user-agent"),
  });

  return redirectTo(request, `${publicEntryPath()}?registered=verify-email`);
}

function redirectTo(request: Request, path: string): NextResponse {
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000";
  const proto = request.headers.get("x-forwarded-proto") || (host.startsWith("localhost") ? "http" : "https");
  return NextResponse.redirect(`${proto}://${host}${path}`, 303);
}

function verificationTokenHash(token: string): string {
  return crypto.createHash("sha256").update(token).digest("hex");
}

function emailVerificationTtlMinutes(): number {
  const value = Number(process.env.EMAIL_VERIFICATION_TOKEN_TTL_MINUTES || 30);
  return Number.isFinite(value) && value > 0 ? value : 30;
}

function clientIp(request: Request): string {
  return (
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    request.headers.get("x-real-ip") ||
    ""
  );
}

function registerRateLimit(): number {
  const value = Number(process.env.REGISTER_RATE_LIMIT_1H || 5);
  return Number.isFinite(value) && value > 0 ? value : 5;
}
