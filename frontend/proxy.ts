import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (!pathname.startsWith("/admin")) return NextResponse.next();

  const username = process.env.ADMIN_BASIC_USER || "";
  const password = process.env.ADMIN_BASIC_PASSWORD || "";

  if (!username || !password) {
    return new NextResponse("Admin access is not configured.", { status: 503 });
  }

  const authorization = request.headers.get("authorization") || "";
  const credentials = parseBasicAuthorization(authorization);

  if (!credentials || credentials.username !== username || credentials.password !== password) {
    return new NextResponse("Authentication required.", {
      status: 401,
      headers: {
        "WWW-Authenticate": 'Basic realm="InboxPilot Admin", charset="UTF-8"',
        "Cache-Control": "no-store",
      },
    });
  }

  const response = NextResponse.next();
  response.headers.set("Cache-Control", "no-store");
  return response;
}

export const config = {
  matcher: ["/admin/:path*"],
};

function parseBasicAuthorization(header: string): { username: string; password: string } | null {
  if (!header.toLowerCase().startsWith("basic ")) return null;

  try {
    const decoded = atob(header.slice(6).trim());
    const separatorIndex = decoded.indexOf(":");
    if (separatorIndex < 0) return null;

    return {
      username: decoded.slice(0, separatorIndex),
      password: decoded.slice(separatorIndex + 1),
    };
  } catch {
    return null;
  }
}
