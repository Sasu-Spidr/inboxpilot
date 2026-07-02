import { NextResponse } from "next/server";

import { currentUser } from "@/lib/auth";
import { publicUrl } from "@/lib/oauthProxy";

export async function GET(request: Request, { params }: { params: Promise<{ provider: string }> }) {
  const user = await currentUser();
  if (!user) return NextResponse.redirect(publicUrl("/", request));

  const { provider } = await params;
  if (!["gmail", "hotmail"].includes(provider)) {
    return NextResponse.redirect(publicUrl("/dashboard", request));
  }

  const url = publicUrl(`/connect/${provider}`, request);
  url.searchParams.set("client", user.clientId);
  url.searchParams.set("account", "main");
  return NextResponse.redirect(url);
}
