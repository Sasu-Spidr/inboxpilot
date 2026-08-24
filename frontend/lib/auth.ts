import crypto from "node:crypto";
import { cookies } from "next/headers";

import { findUserByClientId, type DbUser } from "./db";

const SESSION_COOKIE = "spidr_session";

export type User = {
  clientId: string;
  ownerName: string;
  email: string;
  role: "customer" | "admin";
  status: DbUser["status"];
  emailVerified: boolean;
  sessionVersion: number;
  passwordHash: string;
  passwordSalt: string;
  createdAt: Date;
};

export function toUser(row: DbUser): User {
  return {
    clientId: row.client_id,
    ownerName: row.owner_name,
    email: row.email,
    role: row.role || "customer",
    status: row.status || "ACTIVE",
    emailVerified: Boolean(row.email_verified),
    sessionVersion: Number(row.session_version || 0),
    passwordHash: row.password_hash,
    passwordSalt: row.password_salt,
    createdAt: row.created_at,
  };
}

export function isAdmin(user: User | null): boolean {
  return user?.role === "admin";
}

export function isAccountUsable(user: User | null): boolean {
  return Boolean(user && user.status === "ACTIVE" && user.emailVerified);
}

export function canAccessAdmin(user: User | null): boolean {
  return Boolean(user && isAccountUsable(user) && isAdmin(user));
}

export function slugify(value: string): string {
  const slug = value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "client";
}

export function clientIdFromEmail(email: string): string {
  return slugify(email);
}

export function createPasswordHash(password: string): { hash: string; salt: string } {
  const salt = crypto.randomBytes(16).toString("hex");
  const hash = crypto.scryptSync(password, salt, 64).toString("hex");
  return { hash, salt };
}

export function verifyPassword(password: string, user: User): boolean {
  const hash = crypto.scryptSync(password, user.passwordSalt, 64);
  return crypto.timingSafeEqual(hash, Buffer.from(user.passwordHash, "hex"));
}

export function createSessionToken(clientId: string, sessionVersion: number): string {
  const payload = Buffer.from(JSON.stringify({ clientId, sv: sessionVersion, ts: Date.now() }), "utf-8").toString("base64url");
  const sig = crypto.createHmac("sha256", authSecret()).update(payload).digest("base64url");
  return `${payload}.${sig}`;
}

export function verifySessionToken(token: string): { clientId: string; sessionVersion: number } | null {
  const [payload, sig] = token.split(".");
  if (!payload || !sig) return null;
  const expected = crypto.createHmac("sha256", authSecret()).update(payload).digest("base64url");
  if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) return null;
  const parsed = JSON.parse(Buffer.from(payload, "base64url").toString("utf-8"));
  if (!parsed.clientId || Date.now() - Number(parsed.ts || 0) > sessionMaxAgeSeconds() * 1000) return null;
  return { clientId: parsed.clientId, sessionVersion: Number(parsed.sv || 0) };
}

export async function setSession(clientId: string): Promise<void> {
  const row = await findUserByClientId(clientId);
  const user = row ? toUser(row) : null;
  if (!isAccountUsable(user)) throw new Error("Account is not active");
  const activeUser = user as User;
  const cookieStore = await cookies();
  cookieStore.set(SESSION_COOKIE, createSessionToken(clientId, activeUser.sessionVersion), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: sessionMaxAgeSeconds(),
  });
}

export async function clearSession(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(SESSION_COOKIE);
}

export async function currentUser(): Promise<User | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE)?.value;
  if (!token) return null;
  const session = verifySessionToken(token);
  if (!session) return null;
  const row = await findUserByClientId(session.clientId);
  const user = row ? toUser(row) : null;
  if (!isAccountUsable(user)) return null;
  const activeUser = user as User;
  if (activeUser.sessionVersion !== session.sessionVersion) return null;
  return activeUser;
}

function sessionMaxAgeSeconds(): number {
  const value = Number(process.env.SESSION_MAX_AGE_SECONDS || 60 * 60 * 24);
  return Number.isFinite(value) && value > 0 ? value : 60 * 60 * 24;
}

function authSecret(): string {
  const secret = process.env.AUTH_SECRET || process.env.TOKEN_ENCRYPTION_KEY || "";
  if (!secret) {
    throw new Error("AUTH_SECRET is required");
  }
  return secret;
}
