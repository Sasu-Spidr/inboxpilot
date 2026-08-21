import { Pool } from "pg";

let pool: Pool | null = null;
let initialized = false;

export type DbUser = {
  client_id: string;
  owner_name: string;
  email: string;
  role: "customer" | "admin";
  status: "ACTIVE" | "PENDING_EMAIL_VERIFICATION" | "SUSPENDED_SECURITY" | "DISABLED";
  email_verified: boolean;
  session_version: number;
  security_suspended_at: Date | null;
  security_suspended_reason: string | null;
  last_login_at: Date | null;
  password_hash: string;
  password_salt: string;
  mfa_enabled: boolean;
  mfa_secret: string | null;
  created_at: Date;
};

export function getPool(): Pool {
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) {
    throw new Error("DATABASE_URL is required for frontend authentication");
  }
  if (!pool) {
    pool = new Pool({ connectionString });
  }
  return pool;
}

export async function ensureSchema(): Promise<void> {
  if (initialized) return;
  await getPool().query(`
    create table if not exists users (
      client_id text primary key,
      owner_name text not null,
      email text not null unique,
      role text not null default 'customer',
      password_hash text not null,
      password_salt text not null,
      created_at timestamptz not null default now()
    )
  `);
  await getPool().query("alter table users add column if not exists role text not null default 'customer'");
  await getPool().query("alter table users add column if not exists mfa_enabled boolean not null default false");
  await getPool().query("alter table users add column if not exists mfa_secret text");
  await getPool().query("alter table users add column if not exists status text not null default 'ACTIVE'");
  await getPool().query("alter table users add column if not exists email_verified boolean not null default true");
  await getPool().query("alter table users add column if not exists session_version integer not null default 0");
  await getPool().query("alter table users add column if not exists security_suspended_at timestamptz");
  await getPool().query("alter table users add column if not exists security_suspended_reason text");
  await getPool().query("alter table users add column if not exists last_login_at timestamptz");
  await getPool().query("create index if not exists users_role_idx on users(role)");
  await getPool().query("create index if not exists users_status_idx on users(status)");
  await getPool().query(`
    create table if not exists email_verification_tokens (
      id text primary key,
      client_id text not null references users(client_id) on delete cascade,
      token_hash text not null unique,
      purpose text not null default 'email_verification',
      expires_at timestamptz not null,
      used_at timestamptz,
      created_at timestamptz not null default now()
    )
  `);
  await getPool().query("create index if not exists email_verification_tokens_client_idx on email_verification_tokens(client_id)");
  await getPool().query(`
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
  await getPool().query("create index if not exists security_events_created_idx on security_events(created_at desc)");
  await getPool().query("create index if not exists security_events_type_idx on security_events(event_type)");
  initialized = true;
}

export async function findUserByEmail(email: string): Promise<DbUser | null> {
  await ensureSchema();
  const result = await getPool().query<DbUser>("select * from users where email = $1 limit 1", [email]);
  return result.rows[0] || null;
}

export async function findUserByClientId(clientId: string): Promise<DbUser | null> {
  await ensureSchema();
  const result = await getPool().query<DbUser>("select * from users where client_id = $1 limit 1", [clientId]);
  return result.rows[0] || null;
}

export async function listUsers(): Promise<DbUser[]> {
  await ensureSchema();
  const result = await getPool().query<DbUser>("select * from users order by created_at desc");
  return result.rows;
}

export async function deleteUserByClientId(clientId: string): Promise<void> {
  await ensureSchema();
  await getPool().query("delete from users where client_id = $1", [clientId]);
}

export async function updateUserMfa(
  clientId: string,
  input: { enabled: boolean; secret: string | null },
): Promise<void> {
  await ensureSchema();
  await getPool().query("update users set mfa_enabled = $2, mfa_secret = $3 where client_id = $1", [
    clientId,
    input.enabled,
    input.secret,
  ]);
}

export async function touchLastLogin(clientId: string): Promise<void> {
  await ensureSchema();
  await getPool().query("update users set last_login_at = now() where client_id = $1", [clientId]);
}

export async function updateUserSecurityStatus(
  clientId: string,
  input: {
    status: DbUser["status"];
    reason?: string | null;
    revokeSessions?: boolean;
  },
): Promise<void> {
  await ensureSchema();
  await getPool().query(
    `
    update users
    set status = $2,
        email_verified = case when $2 = 'ACTIVE' then true else email_verified end,
        security_suspended_at = case when $2 = 'SUSPENDED_SECURITY' then now() else security_suspended_at end,
        security_suspended_reason = case when $2 = 'SUSPENDED_SECURITY' then $3 else security_suspended_reason end,
        session_version = session_version + $4
    where client_id = $1
  `,
    [clientId, input.status, input.reason || null, input.revokeSessions ? 1 : 0],
  );
}

export async function createEmailVerificationToken(input: {
  id: string;
  clientId: string;
  tokenHash: string;
  expiresAt: Date;
}): Promise<void> {
  await ensureSchema();
  await getPool().query(
    `
    insert into email_verification_tokens (id, client_id, token_hash, expires_at)
    values ($1, $2, $3, $4)
  `,
    [input.id, input.clientId, input.tokenHash, input.expiresAt],
  );
}

export async function consumeEmailVerificationToken(tokenHash: string): Promise<DbUser | null> {
  await ensureSchema();
  const client = await getPool().connect();
  try {
    await client.query("begin");
    const tokenResult = await client.query<{ client_id: string }>(
      `
      update email_verification_tokens
      set used_at = now()
      where token_hash = $1 and used_at is null and expires_at > now()
      returning client_id
    `,
      [tokenHash],
    );
    const token = tokenResult.rows[0];
    if (!token) {
      await client.query("rollback");
      return null;
    }
    const userResult = await client.query<DbUser>(
      `
      update users
      set status = 'ACTIVE', email_verified = true, session_version = session_version + 1
      where client_id = $1
      returning *
    `,
      [token.client_id],
    );
    await client.query("commit");
    return userResult.rows[0] || null;
  } catch (error) {
    await client.query("rollback");
    throw error;
  } finally {
    client.release();
  }
}

export async function logSecurityEvent(input: {
  eventType: string;
  clientId?: string | null;
  email?: string | null;
  ip?: string | null;
  userAgent?: string | null;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  await ensureSchema();
  await getPool().query(
    `
    insert into security_events (event_type, client_id, email, ip, user_agent, metadata)
    values ($1, $2, $3, $4, $5, $6::jsonb)
  `,
    [
      input.eventType,
      input.clientId || null,
      input.email || null,
      input.ip || null,
      input.userAgent || null,
      JSON.stringify(input.metadata || {}),
    ],
  );
}

export async function createUser(input: {
  clientId: string;
  ownerName: string;
  email: string;
  role?: "customer" | "admin";
  status?: DbUser["status"];
  emailVerified?: boolean;
  passwordHash: string;
  passwordSalt: string;
}): Promise<void> {
  await ensureSchema();
  await getPool().query(
    `
    insert into users (client_id, owner_name, email, role, status, email_verified, password_hash, password_salt)
    values ($1, $2, $3, $4, $5, $6, $7, $8)
  `,
    [
      input.clientId,
      input.ownerName,
      input.email,
      input.role || "customer",
      input.status || "ACTIVE",
      input.emailVerified ?? true,
      input.passwordHash,
      input.passwordSalt,
    ],
  );
}
