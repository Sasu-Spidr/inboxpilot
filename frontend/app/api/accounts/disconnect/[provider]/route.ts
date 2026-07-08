import fs from "node:fs";

import { NextResponse } from "next/server";

import { currentUser } from "@/lib/auth";
import { getClientMailAccounts, type Provider } from "@/lib/clientRegistry";
import { publicUrl } from "@/lib/oauthProxy";
import { resolveTokenFilePath } from "@/lib/paths";

export async function POST(request: Request, { params }: { params: Promise<{ provider: string }> }) {
  const user = await currentUser();
  if (!user) return NextResponse.redirect(publicUrl("/", request));

  const { provider } = await params;
  if (!["gmail", "hotmail"].includes(provider)) {
    return NextResponse.redirect(publicUrl("/dashboard", request));
  }

  const source = new URL(request.url);
  const accountName = source.searchParams.get("account") || "main";
  const providerName = provider as Provider;
  const account = getClientMailAccounts(user.clientId, providerName).find((item) => item.account === accountName);

  if (account) {
    try {
      fs.unlinkSync(resolveTokenFilePath(account.token_file));
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
        throw error;
      }
    }
  }

  return NextResponse.redirect(publicUrl("/dashboard", request));
}
