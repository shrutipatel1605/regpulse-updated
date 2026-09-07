import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Middleware for route protection.
 *
 * Public routes: /, /login, /register, /verify, /library (browsable without auth)
 * Protected routes: /ask, /history, /updates, /saved, /action-items, /account, /admin
 *
 * NOTE: Actual JWT validation happens server-side. This middleware only checks
 * for the presence of a refresh token cookie as a quick client-side gate.
 * The backend auth dependency is the source of truth.
 */

const PUBLIC_PATHS = new Set(["/", "/login", "/register", "/verify", "/pricing"]);
const BROWSABLE_PREFIXES = ["/library", "/s/"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public paths — always accessible
  if (PUBLIC_PATHS.has(pathname)) {
    return NextResponse.next();
  }

  // Library is browsable without auth (search requires auth at API level)
  if (BROWSABLE_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return NextResponse.next();
  }

  // Static assets and API routes — skip
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // For protected routes, check for refresh token cookie
  const refreshToken = request.cookies.get("refresh_token");
  if (!refreshToken) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
