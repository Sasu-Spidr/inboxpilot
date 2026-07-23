import { NextResponse } from "next/server";

import { setSession, toUser, verifyPassword } from "@/lib/auth";
import { findUserByEmail } from "@/lib/db";

export async function POST(request: Request) {
  const form = await request.formData();
  const email = String(form.get("email") || "").trim().toLowerCase();
  const password = String(form.get("password") || "");
  const row = await findUserByEmail(email);
  const user = row ? toUser(row) : null;

  if (!user || !verifyPassword(password, user)) {
    return redirectTo(request, "/connexion?error=login");
  }

  await setSession(user.clientId);
  return redirectTo(request, "/dashboard");
}

function redirectTo(request: Request, path: string): NextResponse {
  const configuredBaseUrl = process.env.FRONTEND_BASE_URL;
  if (configuredBaseUrl) {
    return NextResponse.redirect(new URL(path, configuredBaseUrl).toString(), 303);
  }

  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000";
  const proto = request.headers.get("x-forwarded-proto") || (host.startsWith("localhost") ? "http" : "https");
  return NextResponse.redirect(`${proto}://${host}${path}`, 303);
}
