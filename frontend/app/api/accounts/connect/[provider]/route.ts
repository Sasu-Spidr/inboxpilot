import { NextResponse } from "next/server";

import { currentUser } from "@/lib/auth";

export async function GET(request: Request, { params }: { params: Promise<{ provider: string }> }) {
  const user = await currentUser();
  if (!user) return NextResponse.redirect(new URL("/", request.url));

  const { provider } = await params;
  if (!["gmail", "hotmail"].includes(provider)) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  const oauthBase = process.env.OAUTH_PUBLIC_URL || process.env.OAUTH_BASE_URL || "http://localhost:8080";
  const url = new URL(`/connect/${provider}`, oauthBase);
  url.searchParams.set("client", user.clientId);
  url.searchParams.set("account", "main");
  return NextResponse.redirect(url);
}
