type Bucket = {
  count: number;
  resetAt: number;
};

const buckets = new Map<string, Bucket>();

export function checkRateLimit(input: {
  bucket: string;
  key: string;
  limit: number;
  windowMs: number;
}): { allowed: boolean; remaining: number; resetAt: number } {
  const now = Date.now();
  const mapKey = `${input.bucket}:${input.key || "unknown"}`;
  const current = buckets.get(mapKey);

  if (!current || current.resetAt <= now) {
    const resetAt = now + input.windowMs;
    buckets.set(mapKey, { count: 1, resetAt });
    return { allowed: true, remaining: input.limit - 1, resetAt };
  }

  current.count += 1;
  return {
    allowed: current.count <= input.limit,
    remaining: Math.max(0, input.limit - current.count),
    resetAt: current.resetAt,
  };
}

export function rateLimitKey(...parts: Array<string | null | undefined>): string {
  return parts.map((part) => String(part || "").trim().toLowerCase()).join(":");
}
