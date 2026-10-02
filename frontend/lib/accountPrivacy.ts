import fs from "node:fs";
import path from "node:path";

import { readAgentFlowLogs, deleteAgentFlowLogs } from "./agentFlowLogs";
import { deleteConsentState } from "./consentState";
import { deleteClientMailRegistry, getClientRegistryExport } from "./clientRegistry";
import { deleteClientSettings } from "./clientSettings";
import { accountSecurityEvents, type DbUser } from "./db";
import { deleteActivityEvents, readActivityEvents } from "./dashboardActivity";
import { deleteEntitlementState } from "./entitlementState";
import { dataPath } from "./paths";

export async function exportAccountData(user: DbUser): Promise<Record<string, unknown>> {
  return {
    exported_at: new Date().toISOString(),
    account: {
      client_id: user.client_id,
      owner_name: user.owner_name,
      email: user.email,
      role: user.role,
      status: user.status,
      created_at: user.created_at,
      legal_accepted_at: user.legal_accepted_at,
      legal_version: user.legal_version,
      ai_processing_consent_at: user.ai_processing_consent_at,
      ai_processing_consent_version: user.ai_processing_consent_version,
      subscription_tier: user.subscription_tier,
      subscription_status: user.subscription_status,
    },
    mailboxes: getClientRegistryExport(user.client_id),
    settings: readSettingsExport(user.client_id),
    classified_emails: readActivityEvents(user.client_id),
    agent_logs: readAgentFlowLogs(100_000).filter((event) => event.client_id === user.client_id),
    security_logs: await accountSecurityEvents(user.client_id, user.email),
  };
}

export function deleteAccountFiles(clientId: string): void {
  deleteClientMailRegistry(clientId);
  deleteClientSettings(clientId);
  deleteActivityEvents(clientId);
  deleteAgentFlowLogs(clientId);
  deleteConsentState(clientId);
  deleteEntitlementState(clientId);
  queueProcessedStateDeletion(clientId);
}

function readSettingsExport(clientId: string): Record<string, unknown> {
  const safeId = clientId.replace(/[^a-zA-Z0-9._-]/g, "-");
  const result: Record<string, unknown> = {};
  readJsonInto(result, "default", dataPath("client-settings", `${safeId}.json`));
  const directory = dataPath("client-settings", safeId);
  try {
    for (const file of walkJsonFiles(directory)) {
      const relative = path.relative(directory, file).replaceAll("\\", "/");
      readJsonInto(result, relative, file);
    }
  } catch {
    // The account may only use default settings.
  }
  return result;
}

function walkJsonFiles(directory: string): string[] {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) return walkJsonFiles(target);
    return entry.isFile() && entry.name.endsWith(".json") ? [target] : [];
  });
}

function readJsonInto(result: Record<string, unknown>, key: string, file: string): void {
  try { result[key] = JSON.parse(fs.readFileSync(file, "utf-8")); } catch { /* Missing or invalid file is ignored. */ }
}

function queueProcessedStateDeletion(clientId: string): void {
  const directory = dataPath("deletion-requests");
  fs.mkdirSync(directory, { recursive: true });
  const safeId = clientId.replace(/[^a-zA-Z0-9._-]/g, "_");
  fs.writeFileSync(
    path.join(directory, `${safeId}.json`),
    JSON.stringify({ client_id: clientId, requested_at: new Date().toISOString() }),
    { encoding: "utf-8", mode: 0o600 },
  );
}
