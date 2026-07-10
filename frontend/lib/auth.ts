import crypto from "node:crypto";
import { cookies } from "next/headers";

import { findUserByClientId, type DbUser } from "./db";

const SESSION_COOKIE = "spidr_session";

export type User = {
  clientId: string;
  ownerName: string;
  email: string;
  role: "customer" | "admin";
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
    passwordHash: row.password_hash,
    passwordSalt: row.password_salt,
    createdAt: row.created_at,
  };
}

export function isAdmin(user: User | null): boolean {
  return user?.role === "admin";
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

export function createSessionToken(clientId: string): string {
  const payload = Buffer.from(JSON.stringify({ clientId, ts: Date.now() }), "utf-8").toString("base64url");
  const sig = crypto.createHmac("sha256", authSecret()).update(payload).digest("base64url");
  return `${payload}.${sig}`;
}

export function verifySessionToken(token: string): { clientId: string } | null {
  const [payload, sig] = token.split(".");
  if (!payload || !sig) return null;
  const expected = crypto.createHmac("sha256", authSecret()).update(payload).digest("base64url");
  if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) return null;
  const parsed = JSON.parse(Buffer.from(payload, "base64url").toString("utf-8"));
  if (!parsed.clientId || Date.now() - Number(parsed.ts || 0) > 1000 * 60 * 60 * 24 * 14) return null;
  return { clientId: parsed.clientId };
}

export async function setSession(clientId: string): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set(SESSION_COOKIE, createSessionToken(clientId), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 14,
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
  return row ? toUser(row) : null;
}

function authSecret(): string {
  const secret = process.env.AUTH_SECRET || process.env.TOKEN_ENCRYPTION_KEY || "";
  if (!secret) {
    throw new Error("AUTH_SECRET is required");
  }
  return secret;
}
