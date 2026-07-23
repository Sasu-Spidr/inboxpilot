import { NextResponse } from "next/server";

import { clearSession } from "@/lib/auth";

export async function POST(request: Request) {
  await clearSession();
  return redirectTo(request, "/");
}

function redirectTo(request: Request, path: string): NextResponse {
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "localhost:3000";
  const proto = request.headers.get("x-forwarded-proto") || (host.startsWith("localhost") ? "http" : "https");
  return NextResponse.redirect(`${proto}://${host}${path}`, 303);
}
