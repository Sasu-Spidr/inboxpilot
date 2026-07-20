import fs from "node:fs";
import yaml from "js-yaml";

import { dataPath, resolveTokenFilePath } from "./paths";

export type Provider = "gmail" | "hotmail";

export type MailAccount = {
  account: string;
  email_address?: string;
  connected_at?: string;
  sender_name?: string;
  credentials_file?: string;
  client_id_env?: string;
  client_secret_env?: string;
  tenant_id?: string;
  token_file: string;
};

type ClientRegistry = {
  clients: Record<string, ClientConfig>;
};

type ClientConfig = {
  enabled: boolean;
  owner_name?: string;
  email?: string;
  connectors?: Partial<Record<Provider, ConnectorConfig>>;
};

type ConnectorConfig = {
  enabled: boolean;
  accounts: MailAccount[];
};

export function ensureClientRegistry(clientId: string, ownerName: string, email: string): void {
  const file = dataPath("clients", "clients.yaml");
  fs.mkdirSync(dataPath("clients"), { recursive: true });
  const registry = readRegistry(file);
  registry.clients[clientId] = {
    enabled: true,
    owner_name: ownerName,
    email,
    connectors: {
      gmail: {
        enabled: true,
        accounts: [
          {
            account: "main",
            sender_name: ownerName,
            credentials_file: process.env.GMAIL_OAUTH_CLIENT_FILE || "./secrets/google-oauth-client.json",
            token_file: `./data/tokens/${clientId}-gmail-main.token.enc`,
            connected_at: "",
          },
        ],
      },
      hotmail: {
        enabled: true,
        accounts: [
          {
            account: "main",
            sender_name: ownerName,
            client_id_env: "MICROSOFT_CLIENT_ID",
            client_secret_env: "MICROSOFT_CLIENT_SECRET",
            tenant_id: "consumers",
            token_file: `./data/tokens/${clientId}-hotmail-main.token.enc`,
            connected_at: "",
          },
        ],
      },
    },
  };
  fs.writeFileSync(file, yaml.dump(registry, { noRefs: true, lineWidth: 120 }), "utf-8");
}

export function getClientMailAccounts(clientId: string, provider: Provider): MailAccount[] {
  const registry = readRegistry(registryPath());
  return registry.clients[clientId]?.connectors?.[provider]?.accounts || [];
}

export function deleteClientMailRegistry(clientId: string): void {
  const file = registryPath();
  const registry = readRegistry(file);
  const client = registry.clients[clientId];
  if (!client) return;

  for (const connector of Object.values(client.connectors || {})) {
    for (const account of connector?.accounts || []) {
      safeUnlink(resolveTokenFilePath(account.token_file));
    }
  }

  delete registry.clients[clientId];
  fs.mkdirSync(dataPath("clients"), { recursive: true });
  fs.writeFileSync(file, yaml.dump(registry, { noRefs: true, lineWidth: 120 }), "utf-8");
}

export function removeMailAccount(clientId: string, provider: Provider, accountName: string): boolean {
  const file = registryPath();
  const registry = readRegistry(file);
  const accounts = registry.clients[clientId]?.connectors?.[provider]?.accounts;
  if (!accounts) return false;

  const index = accounts.findIndex((account) => account.account === accountName);
  if (index === -1) return false;

  const [removed] = accounts.splice(index, 1);
  if (removed?.token_file) {
    safeUnlink(resolveTokenFilePath(removed.token_file));
  }

  fs.writeFileSync(file, yaml.dump(registry, { noRefs: true, lineWidth: 120 }), "utf-8");
  return true;
}

export function ensureMailAccount(clientId: string, ownerName: string, email: string, provider: Provider, account = "main"): MailAccount {
  const file = registryPath();
  fs.mkdirSync(dataPath("clients"), { recursive: true });
  const registry = readRegistry(file);
  ensureClientConfig(registry, clientId, ownerName, email);
  ensureConnectorConfig(registry.clients[clientId], provider);

  const accounts = registry.clients[clientId].connectors?.[provider]?.accounts || [];
  const existing = accounts.find((item) => item.account === account);
  if (existing) return existing;

  const created = buildAccountConfig(clientId, ownerName, provider, account);
  accounts.push(created);
  fs.writeFileSync(file, yaml.dump(registry, { noRefs: true, lineWidth: 120 }), "utf-8");
  return created;
}

export function addMailAccount(clientId: string, ownerName: string, email: string, provider: Provider): MailAccount {
  const file = registryPath();
  fs.mkdirSync(dataPath("clients"), { recursive: true });
  const registry = readRegistry(file);
  ensureClientConfig(registry, clientId, ownerName, email);
  ensureConnectorConfig(registry.clients[clientId], provider);

  const accounts = registry.clients[clientId].connectors?.[provider]?.accounts || [];
  const account = nextAccountName(provider, accounts);
  const created = buildAccountConfig(clientId, ownerName, provider, account);
  accounts.push(created);
  fs.writeFileSync(file, yaml.dump(registry, { noRefs: true, lineWidth: 120 }), "utf-8");
  return created;
}

function readRegistry(file: string): ClientRegistry {
  if (!fs.existsSync(file)) return { clients: {} };
  const parsed = yaml.load(fs.readFileSync(file, "utf-8")) as ClientRegistry | null;
  return parsed?.clients ? parsed : { clients: {} };
}

function registryPath(): string {
  return dataPath("clients", "clients.yaml");
}

function ensureClientConfig(registry: ClientRegistry, clientId: string, ownerName: string, email: string): void {
  registry.clients[clientId] ||= {
    enabled: true,
    owner_name: ownerName,
    email,
    connectors: {},
  };
  registry.clients[clientId].connectors ||= {};
}

function ensureConnectorConfig(client: ClientConfig, provider: Provider): void {
  client.connectors ||= {};
  client.connectors[provider] ||= { enabled: true, accounts: [] };
  client.connectors[provider].enabled = true;
  client.connectors[provider].accounts ||= [];
}

function buildAccountConfig(clientId: string, ownerName: string, provider: Provider, account: string): MailAccount {
  const tokenAccount = safeAccountName(account);
  if (provider === "gmail") {
    return {
      account,
      sender_name: ownerName,
      credentials_file: process.env.GMAIL_OAUTH_CLIENT_FILE || "./secrets/google-oauth-client.json",
      token_file: `./data/tokens/${clientId}-gmail-${tokenAccount}.token.enc`,
      connected_at: "",
    };
  }
  return {
    account,
    sender_name: ownerName,
    client_id_env: "MICROSOFT_CLIENT_ID",
    client_secret_env: "MICROSOFT_CLIENT_SECRET",
    tenant_id: "consumers",
    token_file: `./data/tokens/${clientId}-hotmail-${tokenAccount}.token.enc`,
    connected_at: "",
  };
}

function nextAccountName(provider: Provider, accounts: MailAccount[]): string {
  if (accounts.length === 0) return "main";
  const prefix = provider === "gmail" ? "gmail" : "hotmail";
  let index = accounts.length + 1;
  while (accounts.some((item) => item.account === `${prefix}-${index}`)) index += 1;
  return `${prefix}-${index}`;
}

function safeAccountName(account: string): string {
  return account.toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "") || "main";
}

function safeUnlink(file: string): void {
  try {
    fs.unlinkSync(file);
  } catch {
    // The token may not exist yet; deletion of the user should continue.
  }
}
