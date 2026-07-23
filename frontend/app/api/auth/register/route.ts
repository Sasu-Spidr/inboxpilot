import { NextResponse } from "next/server";

import { clientIdFromEmail, createPasswordHash, setSession } from "@/lib/auth";
import { ensureClientRegistry } from "@/lib/clientRegistry";
import { createUser, findUserByEmail } from "@/lib/db";

export async function POST(request: Request) {
  const form = await request.formData();
  const ownerName = String(form.get("ownerName") || "").trim();
  const email = String(form.get("email") || "").trim().toLowerCase();
  const password = String(form.get("password") || "");
  const clientId = clientIdFromEmail(email);

  if (!ownerName || !email || !password || password.length < 8) {
    return redirectTo(request, "/connexion?error=register");
  }

  if (await findUserByEmail(email)) {
    return redirectTo(request, "/connexion?error=exists");
  }

  const { hash, salt } = createPasswordHash(password);
  await createUser({
    clientId,
    ownerName,
    email,
    passwordHash: hash,
    passwordSalt: salt,
  });
  ensureClientRegistry(clientId, ownerName, email);
  await setSession(clientId);

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
