import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const AUTH_COOKIE = "autoradar_token";
const ADMIN_COOKIE = "autoradar_admin_token";

function withNoIndex(response: NextResponse): NextResponse {
  response.headers.set("X-Robots-Tag", "noindex, nofollow");
  return response;
}

export function middleware(request: NextRequest) {
  const token = request.cookies.get(AUTH_COOKIE)?.value;
  const adminToken = request.cookies.get(ADMIN_COOKIE)?.value;
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/admin")) {
    if (pathname === "/admin/login") {
      // Не bounce по cookie — клієнт перевіряє сесію (інакше цикл після logout)
      return withNoIndex(NextResponse.next());
    }
    if (!adminToken) {
      return withNoIndex(NextResponse.redirect(new URL("/admin/login", request.url)));
    }
    return withNoIndex(NextResponse.next());
  }

  if (pathname.startsWith("/app")) {
    if (pathname.startsWith("/app/listing/") || pathname.startsWith("/app/compare")) {
      // Публічні шринг-сторінки в кабінеті — без індексації (контент динамічний / персональний).
      return withNoIndex(NextResponse.next());
    }
    if (!token) {
      const loginUrl = new URL("/auth/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
    return withNoIndex(NextResponse.next());
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
