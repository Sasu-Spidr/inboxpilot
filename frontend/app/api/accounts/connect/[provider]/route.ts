import { NextResponse } from "next/server";

import { currentUser } from "@/lib/auth";
import { addMailAccount, ensureMailAccount, getClientMailAccounts, type Provider } from "@/lib/clientRegistry";
import { mailboxLimit } from "@/lib/features";
import { publicUrl } from "@/lib/oauthProxy";
import { tokenFileExists } from "@/lib/paths";

export async function GET(request: Request, { params }: { params: Promise<{ provider: string }> }) {
  const user = await currentUser();
  if (!user) return NextResponse.redirect(publicUrl("/", request));

  const { provider } = await params;
  if (!["gmail", "hotmail"].includes(provider)) {
    return NextResponse.redirect(publicUrl("/dashboard", request));
  }

  const source = new URL(request.url);
  const providerName = provider as Provider;
  const isNewAccount = source.searchParams.get("new") === "1";
  if (isNewAccount && connectedMailboxCount(user.clientId) >= mailboxLimit(user.subscriptionTier, user.subscriptionStatus)) {
    const target = publicUrl("/dashboard", request);
    target.searchParams.set("upsell", "mailbox-limit");
    return NextResponse.redirect(target);
  }
  const account = source.searchParams.get("new") === "1"
    ? addMailAccount(user.clientId, user.ownerName, user.email, providerName).account
    : ensureMailAccount(user.clientId, user.ownerName, user.email, providerName, source.searchParams.get("account") || "main").account;

  const url = publicUrl(`/connect/${provider}`, request);
  url.searchParams.set("client", user.clientId);
  url.searchParams.set("account", account);
  return NextResponse.redirect(url);
}

function connectedMailboxCount(clientId: string): number {
  return (["gmail", "hotmail"] as const)
    .flatMap((provider) => getClientMailAccounts(clientId, provider))
    .filter((account) => tokenFileExists(account.token_file)).length;
}
