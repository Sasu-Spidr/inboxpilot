import { NextResponse, type NextRequest } from "next/server";

import { currentUser } from "@/lib/auth";
import { getClientSettings, saveClientSettings, type LabelSetting } from "@/lib/clientSettings";

export async function GET() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  return NextResponse.json(getClientSettings(user.clientId));
}

export async function POST(request: NextRequest) {
  const user = await currentUser();
  if (!user) return redirectTo(request, "/?error=1");

  const form = await request.formData();
  const count = Number(form.get("labelCount") || 0);
  const labels: LabelSetting[] = [];
  const previousSettings = getClientSettings(user.clientId);

  for (let index = 0; index < count; index += 1) {
    const key = String(form.get(`labels.${index}.key`) || "");
    if (!key) continue;
    labels.push({
      key,
      name: String(form.get(`labels.${index}.name`) || ""),
      description: String(form.get(`labels.${index}.description`) || ""),
      color: String(form.get(`labels.${index}.color`) || ""),
      prepareDraft: form.get(`labels.${index}.prepareDraft`) === "on",
      autoReply: form.get(`labels.${index}.autoReply`) === "on",
      autoDelete: form.get(`labels.${index}.autoDelete`) === "on",
    });
  }

  const savedSettings = saveClientSettings(user.clientId, labels);
  await syncGmailLabelSettings(user.clientId, removedLabelNames(previousSettings.labels, savedSettings.labels));
  return redirectTo(request, "/settings?saved=1");
}

function removedLabelNames(previousLabels: LabelSetting[], nextLabels: LabelSetting[]): string[] {
  const nextKeys = new Set(nextLabels.map((label) => label.key.trim()).filter(Boolean));
  const nextNames = new Set(nextLabels.map((label) => label.name.trim()).filter(Boolean));
  const removed = new Set<string>();
  for (const label of previousLabels) {
    const key = label.key.trim();
    const name = label.name.trim();
    if ((key && !nextKeys.has(key)) || (name && !nextNames.has(name))) {
      if (name) removed.add(name);
      if (key && key !== name) removed.add(key);
    }
  }
  return [...removed];
}

async function syncGmailLabelSettings(clientId: string, removedLabels: string[]): Promise<void> {
  const internalUrl = process.env.OAUTH_INTERNAL_URL;
  const syncKey = process.env.TOKEN_ENCRYPTION_KEY;
  if (!internalUrl || !syncKey) return;

  try {
    const response = await fetch(new URL("/internal/sync-label-settings", internalUrl), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Sync-Key": syncKey,
      },
      body: JSON.stringify({ client: clientId, removed_labels: removedLabels }),
      cache: "no-store",
    });
    if (!response.ok) {
      console.warn("Gmail label settings sync failed", response.status, await response.text());
    }
  } catch (error) {
    console.warn("Gmail label settings sync failed", error);
  }
}

function redirectTo(request: NextRequest, path: string): NextResponse {
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000";
  const proto = request.headers.get("x-forwarded-proto") || (host.startsWith("localhost") ? "http" : "https");
  return NextResponse.redirect(`${proto}://${host}${path}`, 303);
}
