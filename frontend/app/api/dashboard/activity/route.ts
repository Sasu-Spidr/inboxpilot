import { NextResponse } from "next/server";

import { currentUser } from "@/lib/auth";
import { getClientMailAccounts } from "@/lib/clientRegistry";
import { getDashboardActivity } from "@/lib/dashboardActivity";
import { tokenFileExists } from "@/lib/paths";

export async function GET() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const accounts = [...getClientMailAccounts(user.clientId, "gmail"), ...getClientMailAccounts(user.clientId, "hotmail")];
  const connectedMailboxes = accounts.filter((account) => tokenFileExists(account.token_file)).length;

  return NextResponse.json(
    {
      connectedMailboxes,
      activity: getDashboardActivity(user.clientId),
    },
    {
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
