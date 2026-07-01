import { NextResponse } from "next/server";

const VALID_PROVIDERS = new Set(["gmail", "hotmail"]);

export function isValidProvider(provider: string) {
  return VALID_PROVIDERS.has(provider);
}

export function oauthInternalBase() {
  return process.env.OAUTH_INTERNAL_URL || "http://oauth-onboarding:8080";
}

export async function redirectFromOAuth(request: Request | URL, pathname: string) {
  const source = request instanceof URL ? request : new URL(request.url);
  const target = new URL(pathname, oauthInternalBase());
  target.search = source.search;

  const response = await fetch(target, {
    method: "GET",
    redirect: "manual",
    cache: "no-store",
  });

  const location = response.headers.get("location");
  if (location && response.status >= 300 && response.status < 400) {
    return NextResponse.redirect(location);
  }

  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") || "text/html; charset=utf-8",
    },
  });
}
