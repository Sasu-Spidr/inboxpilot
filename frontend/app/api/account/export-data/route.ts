import { NextResponse } from "next/server";

import { currentUser } from "@/lib/auth";
import { exportAccountData } from "@/lib/accountPrivacy";
import { findUserByClientId, logSecurityEvent } from "@/lib/db";

export async function GET() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Non authentifié" }, { status: 401 });
  const row = await findUserByClientId(user.clientId);
  if (!row) return NextResponse.json({ error: "Compte introuvable" }, { status: 404 });
  const body = JSON.stringify(await exportAccountData(row), null, 2);
  await logSecurityEvent({ eventType: "account_data_exported", clientId: user.clientId, email: user.email });
  return new NextResponse(body, {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "content-disposition": `attachment; filename="inboxpilot-export-${user.clientId}.json"`,
      "cache-control": "no-store",
    },
  });
}
