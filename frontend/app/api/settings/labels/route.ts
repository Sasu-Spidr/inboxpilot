import { NextResponse, type NextRequest } from "next/server";

import { currentUser } from "@/lib/auth";
import { getClientSettings, saveClientSettings, type LabelSetting } from "@/lib/clientSettings";

export async function GET() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  return NextResponse.json(getClientSettings(user.clientId));
}

export async function POST(request: NextRequest) {
  const user = await currentUser();
  if (!user) return NextResponse.redirect(new URL("/?error=1", request.url));

  const form = await request.formData();
  const count = Number(form.get("labelCount") || 0);
  const labels: LabelSetting[] = [];

  for (let index = 0; index < count; index += 1) {
    const key = String(form.get(`labels.${index}.key`) || "");
    if (!key) continue;
    labels.push({
      key,
      name: String(form.get(`labels.${index}.name`) || ""),
      color: String(form.get(`labels.${index}.color`) || ""),
      prepareDraft: form.get(`labels.${index}.prepareDraft`) === "on",
      autoReply: form.get(`labels.${index}.autoReply`) === "on",
      autoDelete: form.get(`labels.${index}.autoDelete`) === "on",
    });
  }

  saveClientSettings(user.clientId, labels);
  return NextResponse.redirect(new URL("/settings?saved=1", request.url));
}
