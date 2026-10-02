import fs from "node:fs";
import path from "node:path";

import { dataPath } from "./paths";

export type ConsentState = {
  granted: boolean;
  version: string | null;
  granted_at: string | null;
  updated_at: string;
};

export function syncConsentState(
  clientId: string,
  grantedAt: Date | null,
  version: string | null,
): void {
  const directory = dataPath("consents");
  const target = path.join(directory, `${safeClientId(clientId)}.json`);
  const temporary = `${target}.${process.pid}.${Date.now()}.${Math.random().toString(16).slice(2)}.tmp`;
  const state: ConsentState = {
    granted: Boolean(grantedAt && version),
    version: version || null,
    granted_at: grantedAt?.toISOString() || null,
    updated_at: new Date().toISOString(),
  };
  fs.mkdirSync(directory, { recursive: true });
  try {
    const current = JSON.parse(fs.readFileSync(target, "utf-8")) as ConsentState;
    if (current.granted === state.granted && current.version === state.version && current.granted_at === state.granted_at) return;
  } catch {
    // A missing or invalid marker is replaced atomically.
  }
  fs.writeFileSync(temporary, JSON.stringify(state, null, 2), { encoding: "utf-8", mode: 0o600 });
  fs.renameSync(temporary, target);
}

export function deleteConsentState(clientId: string): void {
  try {
    fs.unlinkSync(dataPath("consents", `${safeClientId(clientId)}.json`));
  } catch {
    // Missing consent state is already the safe, denied state.
  }
}

function safeClientId(clientId: string): string {
  return clientId.replace(/[^a-zA-Z0-9._-]/g, "_");
}

