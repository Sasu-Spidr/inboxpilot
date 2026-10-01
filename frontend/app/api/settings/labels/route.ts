import { NextResponse, type NextRequest } from "next/server";

import { currentUser } from "@/lib/auth";
import { getClientMailAccounts, type Provider } from "@/lib/clientRegistry";
import { archiveSavedClientSettingsForEmail, DEFAULT_LABEL_SETTINGS, getClientSettings, saveClientSettings, type LabelSetting } from "@/lib/clientSettings";
import { entitlement } from "@/lib/features";
import { oauthInternalBase } from "@/lib/oauthProxy";

export async function GET() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const settings = getClientSettings(user.clientId);
  if (entitlement(user.subscriptionTier, user.subscriptionStatus, "advanced_rules")) {
    return NextResponse.json(settings);
  }
  return NextResponse.json({
    ...settings,
    labels: settings.labels.filter((label) => DEFAULT_LABEL_SETTINGS.some((item) => item.key === label.key)),
  });
}

export async function POST(request: NextRequest) {
  const user = await currentUser();
  if (!user) return redirectTo(request, "/?error=1");

  const form = await request.formData();
  const provider = normalizeProvider(form.get("provider"));
  const account = String(form.get("account") || "").trim();
  const labels: LabelSetting[] = [];
  const previousSettings = getClientSettings(user.clientId, provider, account || undefined);
  const automaticActionsEnabled = entitlement(user.subscriptionTier, user.subscriptionStatus, "automatic_actions");
  const advancedRulesEnabled = entitlement(user.subscriptionTier, user.subscriptionStatus, "advanced_rules");

  const labelCount = Math.max(DEFAULT_LABEL_SETTINGS.length, Math.min(50, Number(form.get("labelCount") || DEFAULT_LABEL_SETTINGS.length)));
  for (let index = 0; index < labelCount; index += 1) {
    const defaults = DEFAULT_LABEL_SETTINGS[index];
    const key = String(form.get(`labels.${index}.key`) || defaults?.key || "").trim();
    const name = String(form.get(`labels.${index}.name`) || defaults?.name || key).trim();
    if (!key || !name) continue;
    const isDefault = DEFAULT_LABEL_SETTINGS.some((item) => item.key === key);
    if (!advancedRulesEnabled && !isDefault) continue;
    const previous = previousSettings.labels.find((item) => item.key === key);
    labels.push({
      key,
      name,
      description: advancedRulesEnabled
        ? String(form.get(`labels.${index}.description`) || "")
        : previous?.description || defaults?.description || "",
      color: String(form.get(`labels.${index}.color`) || ""),
      priority: Number(form.get(`labels.${index}.priority`) || defaults?.priority || 10),
      prepareDraft: automaticActionsEnabled && form.get(`labels.${index}.prepareDraft`) === "on",
      autoReply: automaticActionsEnabled && form.get(`labels.${index}.autoReply`) === "on",
      autoDelete: automaticActionsEnabled && form.get(`labels.${index}.autoDelete`) === "on",
      markAsRead: false,
      autoDeleteUnreadAfterDays: automaticActionsEnabled
        ? parseUnreadDeleteDays(form.get(`labels.${index}.autoDeleteUnreadAfterDays`))
        : null,
    });
  }

  const preservedAdvancedLabels = advancedRulesEnabled
    ? []
    : previousSettings.labels.filter((label) => !DEFAULT_LABEL_SETTINGS.some((item) => item.key === label.key));
  const savedSettings = saveClientSettings(user.clientId, [...labels, ...preservedAdvancedLabels], provider, account || undefined);
  const mailbox = provider && account ? getClientMailAccounts(user.clientId, provider as Provider).find((item) => item.account === account) : undefined;
  if (provider && mailbox?.email_address) {
    archiveSavedClientSettingsForEmail(user.clientId, provider, mailbox.email_address, savedSettings);
  }
  await syncGmailLabelSettings(user.clientId, removedLabelNames(previousSettings.labels, savedSettings.labels), provider, account || undefined);
  const target = provider && account ? `/settings?provider=${encodeURIComponent(provider)}&account=${encodeURIComponent(account)}&saved=1` : "/settings?saved=1";
  return redirectTo(request, target);
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

async function syncGmailLabelSettings(clientId: string, removedLabels: string[], provider?: string, account?: string): Promise<void> {
  try {
    const response = await fetch(new URL("/internal/sync-label-settings", oauthInternalBase()), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ client: clientId, removed_labels: removedLabels, provider, account }),
      cache: "no-store",
    });
    if (!response.ok) {
      console.warn("Gmail label settings sync failed", response.status, await response.text());
    }
  } catch (error) {
    console.warn("Gmail label settings sync failed", error);
  }
}

function normalizeProvider(value: FormDataEntryValue | null): "gmail" | "hotmail" | undefined {
  const provider = String(value || "").trim();
  return provider === "gmail" || provider === "hotmail" ? provider : undefined;
}

function redirectTo(request: NextRequest, path: string): NextResponse {
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000";
  const proto = request.headers.get("x-forwarded-proto") || (host.startsWith("localhost") ? "http" : "https");
  return NextResponse.redirect(`${proto}://${host}${path}`, 303);
}

function parseUnreadDeleteDays(value: FormDataEntryValue | null): number | null {
  const days = Number(value || 0);
  if (!Number.isFinite(days) || days <= 0) return null;
  return Math.min(365, Math.max(1, Math.floor(days)));
}
