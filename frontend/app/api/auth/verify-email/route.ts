import crypto from "node:crypto";
import { NextResponse } from "next/server";

import { setSession, toUser } from "@/lib/auth";
import { ensureClientRegistry } from "@/lib/clientRegistry";
import { consumeEmailVerificationToken, logSecurityEvent } from "@/lib/db";
import { publicEntryPath } from "@/lib/features";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const token = String(url.searchParams.get("token") || "").trim();

  if (!token) {
    return redirectTo(request, `${publicEntryPath()}?error=verify-email`);
  }

  const row = await consumeEmailVerificationToken(verificationTokenHash(token));
  if (!row) {
    await logSecurityEvent({
      eventType: "email_verification_failed",
      ip: clientIp(request),
      userAgent: request.headers.get("user-agent"),
      metadata: { reason: "invalid_or_expired_token" },
    });
    return redirectTo(request, `${publicEntryPath()}?error=verify-email`);
  }

  const user = toUser(row);
  ensureClientRegistry(user.clientId, user.ownerName, user.email);
  await logSecurityEvent({
    eventType: "email_verified",
    clientId: user.clientId,
    email: user.email,
    ip: clientIp(request),
    userAgent: request.headers.get("user-agent"),
  });
  await setSession(user.clientId);
  return redirectTo(request, "/dashboard");
}

function verificationTokenHash(token: string): string {
  return crypto.createHash("sha256").update(token).digest("hex");
}

function redirectTo(request: Request, path: string): NextResponse {
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000";
  const proto = request.headers.get("x-forwarded-proto") || (host.startsWith("localhost") ? "http" : "https");
  return NextResponse.redirect(`${proto}://${host}${path}`, 303);
}

function clientIp(request: Request): string {
  return request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || request.headers.get("x-real-ip") || "";
}
