import fs from "node:fs";

import { dataPath } from "./paths";
import type { SubscriptionTier } from "./db";

type StoredEntitlement = {
  tier: SubscriptionTier;
  status: string;
  updated_at: string;
};

export function syncEntitlementState(clientId: string, tier: SubscriptionTier, status: string): void {
  const directory = dataPath("entitlements");
  const file = entitlementPath(clientId);
  const next: StoredEntitlement = {
    tier,
    status,
    updated_at: new Date().toISOString(),
  };
  try {
    const current = JSON.parse(fs.readFileSync(file, "utf-8")) as Partial<StoredEntitlement>;
    if (current.tier === tier && current.status === status) return;
  } catch {
    // A missing or invalid state is replaced atomically below.
  }
  fs.mkdirSync(directory, { recursive: true });
  const temporary = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, JSON.stringify(next), { encoding: "utf-8", mode: 0o600 });
  fs.renameSync(temporary, file);
}

export function deleteEntitlementState(clientId: string): void {
  try {
    fs.unlinkSync(entitlementPath(clientId));
  } catch {
    // Missing state needs no cleanup.
  }
}

function entitlementPath(clientId: string): string {
  const safeClientId = clientId.replace(/[^a-zA-Z0-9._-]/g, "-");
  return dataPath("entitlements", `${safeClientId}.json`);
}
