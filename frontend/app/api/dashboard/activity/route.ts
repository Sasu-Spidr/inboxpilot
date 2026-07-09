import { NextResponse } from "next/server";

import { currentUser } from "@/lib/auth";
import { getClientMailAccounts } from "@/lib/clientRegistry";
import { getDashboardActivity } from "@/lib/dashboardActivity";
import { tokenFileExists } from "@/lib/paths";

export async function GET() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const gmailAccounts = getClientMailAccounts(user.clientId, "gmail");
  const hotmailAccounts = getClientMailAccounts(user.clientId, "hotmail");
  const accounts = [...gmailAccounts, ...hotmailAccounts];
  const connectedMailboxes = accounts.filter((account) => tokenFileExists(account.token_file)).length;

  return NextResponse.json(
    {
      connectedMailboxes,
      providers: {
        gmail: providerSummary(gmailAccounts),
        hotmail: providerSummary(hotmailAccounts),
      },
      activity: getDashboardActivity(user.clientId),
    },
    {
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}

function providerSummary(accounts: ReturnType<typeof getClientMailAccounts>) {
  const connectedAccounts = accounts.filter((account) => tokenFileExists(account.token_file));
  return {
    connectedCount: connectedAccounts.length,
    accounts: connectedAccounts.map((account) => account.email_address || account.account),
  };
}
