import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const AUTH_COOKIE = "autoradar_token";
const ADMIN_COOKIE = "autoradar_admin_token";

export function middleware(request: NextRequest) {
  const token = request.cookies.get(AUTH_COOKIE)?.value;
  const adminToken = request.cookies.get(ADMIN_COOKIE)?.value;
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/admin")) {
    if (pathname === "/admin/login") {
      // Не bounce по cookie — клієнт перевіряє сесію (інакше цикл після logout)
      return NextResponse.next();
    }
    if (!adminToken) {
      return NextResponse.redirect(new URL("/admin/login", request.url));
    }
    return NextResponse.next();
  }

  if (pathname.startsWith("/app")) {
    if (pathname.startsWith("/app/listing/")) {
      return NextResponse.next();
    }
    if (!token) {
      const loginUrl = new URL("/auth/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // /auth/login більше не редіректимо через наявність cookie:
  // після logout Set-Cookie може не встигнути / не знятись → цикл /app ↔ login + вічний лоадер.

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/app/:path*",
    "/auth/login",
    "/auth/telegram/:path*",
    "/auth/reset-password",
    "/auth/oauth/:path*",
    "/admin/:path*",
  ],
};
