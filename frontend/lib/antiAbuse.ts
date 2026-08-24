const DEFAULT_BLOCKED_DOMAINS = new Set([
  "immenseignite.info",
  "mailinator.com",
  "guerrillamail.com",
  "10minutemail.com",
  "tempmail.com",
  "temp-mail.org",
  "yopmail.com",
  "trashmail.com",
  "dispostable.com",
  "getnada.com",
  "sharklasers.com",
  "moakt.com",
]);

const FREE_EMAIL_DOMAINS = new Set([
  "gmail.com",
  "googlemail.com",
  "outlook.com",
  "hotmail.com",
  "live.com",
  "msn.com",
  "icloud.com",
  "me.com",
  "yahoo.com",
  "proton.me",
  "protonmail.com",
]);

export type SignupAbuseCheck = {
  allowed: boolean;
  reason?: string;
};

export function clientIp(request: Request): string {
  return (
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    request.headers.get("x-real-ip") ||
    ""
  );
}

export function normalizeEmail(email: string): string {
  return String(email || "").trim().toLowerCase();
}

export function emailDomain(email: string): string {
  const normalized = normalizeEmail(email);
  const domain = normalized.split("@")[1] || "";
  return domain.trim().toLowerCase();
}

export function isValidEmail(email: string): boolean {
  const normalized = normalizeEmail(email);
  if (normalized.length > 254) return false;
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/u.test(normalized);
}

export function blockedEmailDomains(): Set<string> {
  const configured = (process.env.SECURITY_BLOCKED_EMAIL_DOMAINS || "")
    .split(",")
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);
  return new Set([...DEFAULT_BLOCKED_DOMAINS, ...configured]);
}

export function signupAccessCodeRequired(): boolean {
  return Boolean(process.env.SIGNUP_ACCESS_CODE);
}

export function signupAccessCodeMatches(value: string): boolean {
  const expected = process.env.SIGNUP_ACCESS_CODE || "";
  if (!expected) return true;
  return String(value || "").trim() === expected;
}

export function checkSignupAbuse(input: {
  ownerName: string;
  email: string;
  honeypot: string;
  startedAt: string;
  accessCode: string;
  userAgent: string | null;
}): SignupAbuseCheck {
  const ownerName = String(input.ownerName || "").trim();
  const email = normalizeEmail(input.email);
  const domain = emailDomain(email);

  if (input.honeypot.trim()) {
    return { allowed: false, reason: "honeypot_filled" };
  }

  if (!isValidEmail(email)) {
    return { allowed: false, reason: "invalid_email" };
  }

  if (!ownerName || ownerName.length < 3 || ownerName.length > 80) {
    return { allowed: false, reason: "invalid_owner_name" };
  }

  if (!/[a-zÀ-ÿ]/iu.test(ownerName) || !/\s/u.test(ownerName)) {
    return { allowed: false, reason: "owner_name_not_human_like" };
  }

  if (blockedEmailDomains().has(domain)) {
    return { allowed: false, reason: "blocked_email_domain" };
  }

  if (looksLikeRandomIdentity(ownerName, email) && !FREE_EMAIL_DOMAINS.has(domain)) {
    return { allowed: false, reason: "random_identity" };
  }

  const startedAt = Number(input.startedAt || 0);
  const minSeconds = signupMinimumSeconds();
  if (Number.isFinite(startedAt) && startedAt > 0 && Date.now() - startedAt < minSeconds * 1000) {
    return { allowed: false, reason: "form_submitted_too_fast" };
  }

  if (!signupAccessCodeMatches(input.accessCode)) {
    return { allowed: false, reason: "invalid_signup_access_code" };
  }

  const userAgent = String(input.userAgent || "").trim().toLowerCase();
  if (!userAgent || userAgent.length < 12) {
    return { allowed: false, reason: "missing_or_short_user_agent" };
  }

  return { allowed: true };
}

export async function verifyTurnstileIfConfigured(input: {
  token: string;
  ip: string;
}): Promise<SignupAbuseCheck> {
  const secret = process.env.TURNSTILE_SECRET_KEY || "";
  if (!secret) return { allowed: true };
  if (!input.token) return { allowed: false, reason: "turnstile_missing" };

  const body = new URLSearchParams();
  body.set("secret", secret);
  body.set("response", input.token);
  if (input.ip) body.set("remoteip", input.ip);

  try {
    const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      body,
    });
    const result = (await response.json()) as { success?: boolean; "error-codes"?: string[] };
    if (result.success) return { allowed: true };
    return { allowed: false, reason: `turnstile_failed:${(result["error-codes"] || []).join(",")}` };
  } catch {
    return { allowed: false, reason: "turnstile_unreachable" };
  }
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function signupMinimumSeconds(): number {
  const value = Number(process.env.SIGNUP_MIN_SECONDS || 3);
  return Number.isFinite(value) && value >= 0 ? value : 3;
}

function looksLikeRandomIdentity(ownerName: string, email: string): boolean {
  const localPart = normalizeEmail(email).split("@")[0] || "";
  const cleanName = ownerName.toLowerCase().replace(/[^a-z]/g, "");
  const cleanLocal = localPart.toLowerCase().replace(/[^a-z]/g, "");
  if (cleanName.length < 8 && cleanLocal.length < 8) return false;

  return hasLowVowelRatio(cleanName) || hasLowVowelRatio(cleanLocal) || hasLongConsonantRun(cleanName) || hasLongConsonantRun(cleanLocal);
}

function hasLowVowelRatio(value: string): boolean {
  if (value.length < 8) return false;
  const vowels = value.match(/[aeiouy]/g)?.length || 0;
  return vowels / value.length < 0.18;
}

function hasLongConsonantRun(value: string): boolean {
  return /[bcdfghjklmnpqrstvwxz]{6,}/i.test(value);
}
