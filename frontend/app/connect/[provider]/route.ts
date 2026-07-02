import { NextResponse } from "next/server";

import { currentUser } from "@/lib/auth";
import { isValidProvider, publicUrl, redirectFromOAuth } from "@/lib/oauthProxy";

export async function GET(request: Request, { params }: { params: Promise<{ provider: string }> }) {
  const user = await currentUser();
  if (!user) return NextResponse.redirect(publicUrl("/", request));

  const { provider } = await params;
  if (!isValidProvider(provider)) {
    return NextResponse.redirect(publicUrl("/dashboard", request));
  }

  const url = new URL(request.url);
  url.searchParams.set("client", user.clientId);
  url.searchParams.set("account", url.searchParams.get("account") || "main");

  return redirectFromOAuth(url, `/connect/${provider}`);
}
