type FrontendSecretName =
  | "DATABASE_URL"
  | "AUTH_SECRET"
  | "TURNSTILE_SECRET_KEY"
  | "SIGNUP_ACCESS_CODE";

type SecretLocation = {
  path: string;
  field: string;
};

type BaoPayload = {
  data?: {
    data?: Record<string, unknown>;
  };
};

type SecretState = {
  values: Partial<Record<FrontendSecretName, string>>;
  preloadPromise?: Promise<void>;
  loaded: boolean;
};

const SECRET_LOCATIONS: Record<FrontendSecretName, SecretLocation> = {
  DATABASE_URL: {
    path: "secret/data/inboxpilot/database",
    field: "database_url",
  },
  AUTH_SECRET: {
    path: "secret/data/inboxpilot/frontend",
    field: "auth_secret",
  },
  TURNSTILE_SECRET_KEY: {
    path: "secret/data/inboxpilot/frontend",
    field: "turnstile_secret_key",
  },
  SIGNUP_ACCESS_CODE: {
    path: "secret/data/inboxpilot/frontend",
    field: "signup_access_code",
  },
};

const STATE_KEY = Symbol.for("inboxpilot.frontendBaoSecrets");

function state(): SecretState {
  const root = globalThis as typeof globalThis & { [STATE_KEY]?: SecretState };
  root[STATE_KEY] ||= { values: {}, loaded: false };
  return root[STATE_KEY];
}

function agentAddress(): string {
  return (process.env.BAO_AGENT_ADDR || "http://bao-agent-frontend:8100").replace(/\/+$/, "");
}

async function readPath(path: string): Promise<Record<string, unknown>> {
  const url = `${agentAddress()}/v1/${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(5_000),
    });
  } catch (error) {
    throw new Error(`Unable to reach the OpenBao frontend agent for ${path}`, { cause: error });
  }
  if (!response.ok) {
    throw new Error(`OpenBao frontend agent rejected ${path} with HTTP ${response.status}`);
  }
  const payload = (await response.json()) as BaoPayload;
  const values = payload.data?.data;
  if (!values || typeof values !== "object") {
    throw new Error(`Invalid OpenBao response for required path ${path}`);
  }
  return values;
}

async function loadSecrets(): Promise<void> {
  const pathCache = new Map<string, Record<string, unknown>>();
  const loaded: Partial<Record<FrontendSecretName, string>> = {};

  for (const [name, location] of Object.entries(SECRET_LOCATIONS) as [FrontendSecretName, SecretLocation][]) {
    let values = pathCache.get(location.path);
    if (!values) {
      values = await readPath(location.path);
      pathCache.set(location.path, values);
    }
    if (!Object.prototype.hasOwnProperty.call(values, location.field)) {
      throw new Error(`Required OpenBao frontend secret is missing: ${name} (${location.path} field ${location.field})`);
    }
    const value = values[location.field];
    if (typeof value !== "string") {
      throw new Error(`Required OpenBao frontend secret has an invalid type: ${name}`);
    }
    loaded[name] = value;
  }

  const current = state();
  current.values = loaded;
  current.loaded = true;
}

export async function preload(): Promise<void> {
  const current = state();
  if (current.loaded) return;
  if (!current.preloadPromise) {
    current.preloadPromise = loadSecrets().catch((error) => {
      current.preloadPromise = undefined;
      throw error;
    });
  }
  await current.preloadPromise;
}

export function secret(name: FrontendSecretName): string {
  const current = state();
  if (!current.loaded || !Object.prototype.hasOwnProperty.call(current.values, name)) {
    throw new Error(`OpenBao frontend secret was not preloaded: ${name}`);
  }
  return current.values[name] as string;
}

