import { Pool } from "pg";

let pool: Pool | null = null;
let initialized = false;

export type DbUser = {
  client_id: string;
  owner_name: string;
  email: string;
  role: "customer" | "admin";
  password_hash: string;
  password_salt: string;
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
  await getPool().query("create index if not exists users_role_idx on users(role)");
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

export async function createUser(input: {
  clientId: string;
  ownerName: string;
  email: string;
  role?: "customer" | "admin";
  passwordHash: string;
  passwordSalt: string;
}): Promise<void> {
  await ensureSchema();
  await getPool().query(
    `
    insert into users (client_id, owner_name, email, role, password_hash, password_salt)
    values ($1, $2, $3, $4, $5, $6)
  `,
    [input.clientId, input.ownerName, input.email, input.role || "customer", input.passwordHash, input.passwordSalt],
  );
}
