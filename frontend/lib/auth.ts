import crypto from "node:crypto";
import { cookies } from "next/headers";

import { findUserByClientId, type DbUser } from "./db";
import { adminMfaRequired } from "./features";

const SESSION_COOKIE = "spidr_session";
const MFA_PENDING_COOKIE = "spidr_mfa_pending";

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
  mfaEnabled: boolean;
  mfaSecret: string | null;
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
    mfaEnabled: Boolean(row.mfa_enabled),
    mfaSecret: row.mfa_secret ? readMfaSecretFromStorage(row.mfa_secret) : null,
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
  if (!user || !isAccountUsable(user) || !isAdmin(user)) return false;
  return !adminMfaRequired() || user.mfaEnabled;
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

export function generateMfaSecret(): string {
  return base32Encode(crypto.randomBytes(20));
}

export function mfaIssuer(): string {
  return "InboxPilot";
}

export function mfaOtpAuthUrl(user: User, secret: string): string {
  const label = encodeURIComponent(`${mfaIssuer()}:${user.email}`);
  const params = new URLSearchParams({
    secret,
    issuer: mfaIssuer(),
    algorithm: "SHA1",
    digits: "6",
    period: "30",
  });
  return `otpauth://totp/${label}?${params.toString()}`;
}

export function encryptMfaSecret(secret: string): string {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", mfaEncryptionKey(), iv);
  const ciphertext = Buffer.concat([cipher.update(secret, "utf-8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return `enc:v1:${iv.toString("base64url")}:${tag.toString("base64url")}:${ciphertext.toString("base64url")}`;
}

export function verifyTotp(code: string, secret: string, window = 1): boolean {
  const normalized = code.replace(/\s+/g, "");
  if (!/^\d{6}$/.test(normalized)) return false;
  const now = Math.floor(Date.now() / 1000 / 30);
  for (let offset = -window; offset <= window; offset += 1) {
    const expected = hotp(secret, now + offset);
    if (crypto.timingSafeEqual(Buffer.from(normalized), Buffer.from(expected))) return true;
  }
  return false;
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
  cookieStore.delete(MFA_PENDING_COOKIE);
}

export async function clearSession(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(SESSION_COOKIE);
  cookieStore.delete(MFA_PENDING_COOKIE);
}

export function createMfaPendingToken(clientId: string): string {
  const payload = Buffer.from(JSON.stringify({ clientId, ts: Date.now(), purpose: "mfa" }), "utf-8").toString("base64url");
  const sig = crypto.createHmac("sha256", authSecret()).update(payload).digest("base64url");
  return `${payload}.${sig}`;
}

export function verifyMfaPendingToken(token: string): { clientId: string } | null {
  const [payload, sig] = token.split(".");
  if (!payload || !sig) return null;
  const expected = crypto.createHmac("sha256", authSecret()).update(payload).digest("base64url");
  if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) return null;
  const parsed = JSON.parse(Buffer.from(payload, "base64url").toString("utf-8"));
  if (parsed.purpose !== "mfa" || !parsed.clientId || Date.now() - Number(parsed.ts || 0) > 1000 * 60 * 10) return null;
  return { clientId: parsed.clientId };
}

export async function setMfaPending(clientId: string): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set(MFA_PENDING_COOKIE, createMfaPendingToken(clientId), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 10,
  });
}

export async function currentMfaPendingUser(): Promise<User | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(MFA_PENDING_COOKIE)?.value;
  if (!token) return null;
  const pending = verifyMfaPendingToken(token);
  if (!pending) return null;
  const row = await findUserByClientId(pending.clientId);
  const user = row ? toUser(row) : null;
  return isAccountUsable(user) ? user : null;
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

function readMfaSecretFromStorage(value: string): string {
  if (!value.startsWith("enc:v1:")) return value;
  const [, , iv, tag, ciphertext] = value.split(":");
  if (!iv || !tag || !ciphertext) throw new Error("Invalid encrypted MFA secret");
  const decipher = crypto.createDecipheriv("aes-256-gcm", mfaEncryptionKey(), Buffer.from(iv, "base64url"));
  decipher.setAuthTag(Buffer.from(tag, "base64url"));
  return Buffer.concat([decipher.update(Buffer.from(ciphertext, "base64url")), decipher.final()]).toString("utf-8");
}

function mfaEncryptionKey(): Buffer {
  return crypto.createHash("sha256").update(authSecret()).digest();
}

const BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

function base32Encode(input: Buffer): string {
  let bits = "";
  for (const byte of input) bits += byte.toString(2).padStart(8, "0");
  let output = "";
  for (let i = 0; i < bits.length; i += 5) {
    const chunk = bits.slice(i, i + 5).padEnd(5, "0");
    output += BASE32_ALPHABET[parseInt(chunk, 2)];
  }
  return output;
}

function base32Decode(input: string): Buffer {
  const clean = input.toUpperCase().replace(/=+$/g, "").replace(/\s+/g, "");
  let bits = "";
  for (const char of clean) {
    const value = BASE32_ALPHABET.indexOf(char);
    if (value === -1) throw new Error("Invalid MFA secret");
    bits += value.toString(2).padStart(5, "0");
  }
  const bytes: number[] = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) {
    bytes.push(parseInt(bits.slice(i, i + 8), 2));
  }
  return Buffer.from(bytes);
}

function hotp(secret: string, counter: number): string {
  const key = base32Decode(secret);
  const msg = Buffer.alloc(8);
  msg.writeUInt32BE(Math.floor(counter / 0x100000000), 0);
  msg.writeUInt32BE(counter >>> 0, 4);
  const hmac = crypto.createHmac("sha1", key).update(msg).digest();
  const offset = hmac[hmac.length - 1] & 0xf;
  const code =
    ((hmac[offset] & 0x7f) << 24) |
    ((hmac[offset + 1] & 0xff) << 16) |
    ((hmac[offset + 2] & 0xff) << 8) |
    (hmac[offset + 3] & 0xff);
  return String(code % 1_000_000).padStart(6, "0");
}
