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
  return tokenFileExists(dataPath("tokens", file));
}

export function tokenFileExists(tokenFile: string): boolean {
  const file = tokenFile.startsWith("./data/") ? dataPath(tokenFile.replace("./data/", "")) : tokenFile;
  try {
    return fs.existsSync(file);
  } catch {
    return false;
  }
}
