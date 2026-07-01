import fs from "node:fs";
import yaml from "js-yaml";

import { dataPath } from "./paths";

type ClientRegistry = {
  clients: Record<string, unknown>;
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
            tenant_id: "consumers",
            token_file: `./data/tokens/${clientId}-hotmail-main.token.enc`,
          },
        ],
      },
    },
  };
  fs.writeFileSync(file, yaml.dump(registry, { noRefs: true, lineWidth: 120 }), "utf-8");
}

function readRegistry(file: string): ClientRegistry {
  if (!fs.existsSync(file)) return { clients: {} };
  const parsed = yaml.load(fs.readFileSync(file, "utf-8")) as ClientRegistry | null;
  return parsed?.clients ? parsed : { clients: {} };
}
