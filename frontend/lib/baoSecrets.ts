type FrontendSecretName =
  | "DATABASE_URL"
  | "AUTH_SECRET"
  | "TURNSTILE_SECRET_KEY"
  | "SIGNUP_ACCESS_CODE"
  | "STRIPE_SECRET_KEY"
  | "STRIPE_WEBHOOK_SECRET";

type SecretLocation = {
  path: string;
  field: string;
  /** Missing optional secrets disable the feature that needs them instead of blocking startup. */
  optional?: boolean;
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
  STRIPE_SECRET_KEY: {
    path: "secret/data/inboxpilot/frontend",
    field: "stripe_secret_key",
    optional: true,
  },
  STRIPE_WEBHOOK_SECRET: {
    path: "secret/data/inboxpilot/frontend",
    field: "stripe_webhook_secret",
    optional: true,
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
  const pathCache = new Map<string, Record<string, unknown> | null>();
  const loaded: Partial<Record<FrontendSecretName, string>> = {};

  for (const [name, location] of Object.entries(SECRET_LOCATIONS) as [FrontendSecretName, SecretLocation][]) {
    let values = pathCache.get(location.path);
    if (values === undefined) {
      try {
        values = await readPath(location.path);
      } catch (error) {
        if (!location.optional) throw error;
        values = null;
      }
      pathCache.set(location.path, values);
    }
    if (values === null) {
      if (location.optional) continue;
      throw new Error(`Required OpenBao frontend secret is unreachable: ${name} (${location.path})`);
    }
    if (!Object.prototype.hasOwnProperty.call(values, location.field)) {
      if (location.optional) continue;
      throw new Error(`Required OpenBao frontend secret is missing: ${name} (${location.path} field ${location.field})`);
    }
    const value = values[location.field];
    if (typeof value !== "string") {
      if (location.optional) continue;
      throw new Error(`Required OpenBao frontend secret has an invalid type: ${name}`);
    }
    if (location.optional && !value) continue;
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

/** Same as `secret`, but returns undefined for an optional secret that OpenBao does not hold. */
export function optionalSecret(name: FrontendSecretName): string | undefined {
  const current = state();
  if (!current.loaded) return undefined;
  return current.values[name];
}

