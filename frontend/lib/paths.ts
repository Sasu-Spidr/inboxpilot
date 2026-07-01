import path from "node:path";
import fs from "node:fs";

export function dataDir(): string {
  return process.env.DATA_DIR || path.join(process.cwd(), "..", "data");
}

export function dataPath(...parts: string[]): string {
  return path.join(dataDir(), ...parts);
}

export function tokenExists(clientId: string, provider: "gmail" | "hotmail"): boolean {
  const file = provider === "gmail" ? `${clientId}-gmail-main.token.enc` : `${clientId}-hotmail-main.token.enc`;
  try {
    return fs.existsSync(dataPath("tokens", file));
  } catch {
    return false;
  }
}
