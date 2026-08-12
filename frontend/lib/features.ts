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

export function publicEntryPath(): string {
  return landingEnabled() ? "/" : "/connexion";
}
