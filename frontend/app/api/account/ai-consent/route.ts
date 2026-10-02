import { NextResponse } from "next/server";

import { currentUser } from "@/lib/auth";
import { syncConsentState } from "@/lib/consentState";
import { logSecurityEvent, recordAiProcessingConsent } from "@/lib/db";
import { AI_CONSENT_VERSION } from "@/lib/privacy";

export async function POST(request: Request) {
  const user = await currentUser();
  if (!user) return NextResponse.redirect(new URL("/connexion", request.url), 303);
  if (!sameOrigin(request)) return NextResponse.json({ error: "Origine refusée" }, { status: 403 });
  const row = await recordAiProcessingConsent(user.clientId, AI_CONSENT_VERSION);
  if (!row) return NextResponse.json({ error: "Compte introuvable" }, { status: 404 });
  syncConsentState(user.clientId, row.ai_processing_consent_at, row.ai_processing_consent_version);
  await logSecurityEvent({ eventType: "ai_processing_consent_granted", clientId: user.clientId, email: user.email, metadata: { version: AI_CONSENT_VERSION } });
  return NextResponse.redirect(new URL("/dashboard?privacy=consent-recorded", request.url), 303);
}

function sameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  const expectedHost = request.headers.get("x-forwarded-host") || request.headers.get("host");
  try { return new URL(origin).host === expectedHost; } catch { return false; }
}
