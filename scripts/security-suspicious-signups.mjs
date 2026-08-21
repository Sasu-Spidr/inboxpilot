#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";

import pg from "pg";
import yaml from "js-yaml";

const { Pool } = pg;

const args = parseArgs(process.argv.slice(2));
const domain = String(args.domain || "").trim().toLowerCase().replace(/^@/, "");
const suspend = Boolean(args.suspend);
const confirm = Boolean(args.confirm);

if (!domain) fail("Usage: npm run security:suspicious-signups -- --domain immenseignite.info [--dry-run|--suspend --confirm]");
if (suspend && !confirm) fail("Suspension refused: add --confirm after --suspend.");

const root = fs.existsSync(path.join(process.cwd(), "frontend")) ? process.cwd() : path.resolve(process.cwd(), "..");
const dataDir = process.env.DATA_DIR || path.join(root, "data");
const registryFile = process.env.CLIENT_REGISTRY_FILE || path.join(dataDir, "clients", "clients.yaml");
const reportDir = path.join(root, "SECURITE");
const databaseUrl = process.env.DATABASE_URL;

if (!databaseUrl) fail("DATABASE_URL is required.");

const pool = new Pool({ connectionString: databaseUrl });

try {
  await ensureSecurityColumns();
  const result = await pool.query(
    `
    select client_id, owner_name, email, status, email_verified, session_version, created_at, last_login_at
    from users
    where lower(split_part(email, '@', 2)) = $1
    order by created_at desc
  `,
    [domain],
  );

  const registry = readRegistry();
  const rows = result.rows.map((row) => summarizeUser(row, registry));
  const payload = {
    generated_at: new Date().toISOString(),
    mode: suspend ? "suspend_confirmed" : "dry_run",
    searched_domain: domain,
    total_accounts: rows.length,
    accounts: rows,
  };

  fs.mkdirSync(reportDir, { recursive: true });
  const reportPath = path.join(reportDir, `suspicious-signups-${safeDate()}.json`);
  fs.writeFileSync(reportPath, JSON.stringify(payload, null, 2), "utf-8");

  if (suspend) {
    await suspendUsers(result.rows, domain);
    disableRegistryClients(registry, result.rows.map((row) => row.client_id), domain);
    writeRegistry(registry);
  }

  console.log(`${suspend ? "Suspension" : "Dry-run"} completed.`);
  console.log(`Domain: ${domain}`);
  console.log(`Accounts matched: ${rows.length}`);
  console.log(`Report: ${reportPath}`);
  console.log("No secret, OAuth token or password was printed.");
} finally {
  await pool.end();
}

async function ensureSecurityColumns() {
  await pool.query("alter table users add column if not exists status text not null default 'ACTIVE'");
  await pool.query("alter table users add column if not exists email_verified boolean not null default true");
  await pool.query("alter table users add column if not exists session_version integer not null default 0");
  await pool.query("alter table users add column if not exists security_suspended_at timestamptz");
  await pool.query("alter table users add column if not exists security_suspended_reason text");
  await pool.query("alter table users add column if not exists last_login_at timestamptz");
  await pool.query(`
    create table if not exists security_events (
      id bigserial primary key,
      event_type text not null,
      client_id text,
      email text,
      ip text,
      user_agent text,
      metadata jsonb not null default '{}'::jsonb,
      created_at timestamptz not null default now()
    )
  `);
}

async function suspendUsers(users, domainName) {
  for (const user of users) {
    await pool.query(
      `
      update users
      set status = 'SUSPENDED_SECURITY',
          security_suspended_at = now(),
          security_suspended_reason = $2,
          session_version = session_version + 1
      where client_id = $1
    `,
      [user.client_id, `Suspicious signup domain: ${domainName}`],
    );
    await pool.query(
      `
      insert into security_events (event_type, client_id, email, metadata)
      values ('account_suspended_security', $1, $2, $3::jsonb)
    `,
      [user.client_id, user.email, JSON.stringify({ reason: "suspicious_signup_domain", domain: domainName })],
    );
  }
}

function summarizeUser(row, registry) {
  const clientCfg = registry.clients?.[row.client_id] || {};
  const connectors = clientCfg.connectors || {};
  return {
    client_ref: pseudonym(row.client_id),
    email_domain: String(row.email || "").split("@")[1] || "",
    status: row.status || "ACTIVE",
    email_verified: Boolean(row.email_verified),
    created_at: row.created_at,
    last_login_at: row.last_login_at || null,
    session_presence: "non_determinable_stateless_cookie",
    registry_enabled: clientCfg.enabled !== false,
    oauth_tokens: {
      gmail: connectedAccounts(connectors.gmail),
      hotmail: connectedAccounts(connectors.hotmail),
    },
  };
}

function connectedAccounts(connector) {
  const accounts = connector?.accounts || [];
  return {
    total: accounts.length,
    connected: accounts.filter((account) => tokenExists(account.token_file)).length,
  };
}

function tokenExists(tokenFile) {
  if (!tokenFile) return false;
  const resolved = tokenFile.startsWith("./data/")
    ? path.join(dataDir, tokenFile.replace("./data/", ""))
    : path.resolve(root, tokenFile);
  return fs.existsSync(resolved);
}

function disableRegistryClients(registry, clientIds, domainName) {
  registry.clients ||= {};
  for (const clientId of clientIds) {
    if (!registry.clients[clientId]) continue;
    registry.clients[clientId].enabled = false;
    registry.clients[clientId].security_status = "SUSPENDED_SECURITY";
    registry.clients[clientId].security_suspended_at = new Date().toISOString();
    registry.clients[clientId].security_suspended_reason = `Suspicious signup domain: ${domainName}`;
  }
}

function readRegistry() {
  if (!fs.existsSync(registryFile)) return { clients: {} };
  return yaml.load(fs.readFileSync(registryFile, "utf-8")) || { clients: {} };
}

function writeRegistry(registry) {
  fs.mkdirSync(path.dirname(registryFile), { recursive: true });
  fs.writeFileSync(registryFile, yaml.dump(registry, { sortKeys: false, lineWidth: 120 }), "utf-8");
}

function parseArgs(values) {
  const output = {};
  for (let index = 0; index < values.length; index += 1) {
    const item = values[index];
    if (!item.startsWith("--")) continue;
    const key = item.slice(2);
    const next = values[index + 1];
    if (!next || next.startsWith("--")) {
      output[key] = true;
    } else {
      output[key] = next;
      index += 1;
    }
  }
  return output;
}

function pseudonym(value) {
  return crypto.createHash("sha256").update(String(value)).digest("hex").slice(0, 16);
}

function safeDate() {
  return new Date().toISOString().replace(/[:.]/g, "-");
}

function fail(message) {
  console.error(message);
  process.exit(1);
}
