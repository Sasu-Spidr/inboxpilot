import { NextResponse } from "next/server";

import { isValidProvider, redirectFromOAuth } from "@/lib/oauthProxy";

export async function GET(request: Request, { params }: { params: Promise<{ provider: string }> }) {
  const { provider } = await params;
  if (!isValidProvider(provider)) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return redirectFromOAuth(request, `/oauth/${provider}/callback`);
}
