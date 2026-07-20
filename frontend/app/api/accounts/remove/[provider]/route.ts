import { NextResponse } from "next/server";

import { currentUser } from "@/lib/auth";
import { removeMailAccount, type Provider } from "@/lib/clientRegistry";
import { publicUrl } from "@/lib/oauthProxy";

export async function POST(request: Request, { params }: { params: Promise<{ provider: string }> }) {
  const user = await currentUser();
  if (!user) return NextResponse.redirect(publicUrl("/", request));

  const { provider } = await params;
  if (!["gmail", "hotmail"].includes(provider)) {
    return NextResponse.redirect(publicUrl("/dashboard", request));
  }

  const source = new URL(request.url);
  const accountName = source.searchParams.get("account") || "";
  if (accountName) {
    removeMailAccount(user.clientId, provider as Provider, accountName);
  }

  return NextResponse.redirect(publicUrl("/dashboard", request));
}
