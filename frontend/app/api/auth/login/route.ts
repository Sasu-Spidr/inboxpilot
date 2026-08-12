import { NextResponse } from "next/server";

import { setMfaPending, setSession, toUser, verifyPassword } from "@/lib/auth";
import { findUserByEmail } from "@/lib/db";
import { mfaFeatureEnabled, publicEntryPath } from "@/lib/features";

export async function POST(request: Request) {
  const form = await request.formData();
  const email = String(form.get("email") || "").trim().toLowerCase();
  const password = String(form.get("password") || "");
  const row = await findUserByEmail(email);
  const user = row ? toUser(row) : null;

  if (!user || !verifyPassword(password, user)) {
    return redirectTo(request, `${publicEntryPath()}?error=login`);
  }

  if (mfaFeatureEnabled() && user.mfaEnabled) {
    await setMfaPending(user.clientId);
    return redirectTo(request, "/mfa");
  }

  await setSession(user.clientId);
  return redirectTo(request, "/dashboard");
}

function redirectTo(request: Request, path: string): NextResponse {
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000";
  const proto = request.headers.get("x-forwarded-proto") || (host.startsWith("localhost") ? "http" : "https");
  return NextResponse.redirect(`${proto}://${host}${path}`, 303);
}
