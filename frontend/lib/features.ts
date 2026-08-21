export function privateClientMode(): boolean {
  return process.env.INBOXPILOT_PRIVATE_CLIENT_MODE === "true";
}

export function landingEnabled(): boolean {
  if (privateClientMode()) return process.env.INBOXPILOT_ENABLE_LANDING === "true";
  return process.env.INBOXPILOT_ENABLE_LANDING !== "false";
}

export function mfaFeatureEnabled(): boolean {
  if (privateClientMode()) return process.env.INBOXPILOT_ENABLE_MFA === "true";
  return process.env.INBOXPILOT_ENABLE_MFA !== "false";
}

export function publicSignupEnabled(): boolean {
  return process.env.PUBLIC_SIGNUP_ENABLED === "true";
}

export function adminMfaRequired(): boolean {
  if (!mfaFeatureEnabled()) return false;
  return process.env.ADMIN_MFA_REQUIRED !== "false";
}

export function publicEntryPath(): string {
  return landingEnabled() ? "/" : "/connexion";
}
