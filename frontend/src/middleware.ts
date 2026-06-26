import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const AUTH_COOKIE = "autoradar_token";
const ADMIN_COOKIE = "autoradar_admin_token";
const PUBLIC_AUTH_PATHS = ["/auth/login", "/auth/telegram", "/auth/reset-password", "/auth/oauth", "/auth/telegram/login"];

export function middleware(request: NextRequest) {
  const token = request.cookies.get(AUTH_COOKIE)?.value;
  const adminToken = request.cookies.get(ADMIN_COOKIE)?.value;
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/admin")) {
    if (pathname === "/admin/login") {
      if (adminToken) return NextResponse.redirect(new URL("/admin", request.url));
      return NextResponse.next();
    }
    if (!adminToken) {
      return NextResponse.redirect(new URL("/admin/login", request.url));
    }
    return NextResponse.next();
  }

  if (pathname.startsWith("/app")) {
    if (!token) {
      const loginUrl = new URL("/auth/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  if (PUBLIC_AUTH_PATHS.some(p => pathname.startsWith(p)) && token) {
    const redirect = request.nextUrl.searchParams.get("redirect");
    const destination = redirect?.startsWith("/app") ? redirect : "/app/dashboard";
    if (pathname.startsWith("/auth/login")) {
      return NextResponse.redirect(new URL(destination, request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/app/:path*", "/auth/login", "/auth/telegram/:path*", "/auth/reset-password", "/auth/oauth/:path*", "/admin/:path*"],
};
