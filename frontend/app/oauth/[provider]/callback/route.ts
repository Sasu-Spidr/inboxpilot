import { NextResponse } from "next/server";

import { isValidProvider, publicUrl, redirectFromOAuth } from "@/lib/oauthProxy";

export async function GET(request: Request, { params }: { params: Promise<{ provider: string }> }) {
  const { provider } = await params;
  if (!isValidProvider(provider)) {
    return NextResponse.redirect(publicUrl("/dashboard", request));
  }

  return redirectFromOAuth(request, `/oauth/${provider}/callback`);
}
