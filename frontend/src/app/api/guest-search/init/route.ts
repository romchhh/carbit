import { NextRequest, NextResponse } from "next/server";
import {
  GUEST_SEARCH_COOKIE,
  guestSearchCookieOptions,
  issueGuestSearchToken,
} from "@/lib/server/guest-search-token";
import { isAllowedGuestSearchRequest } from "@/lib/server/guest-search-origin";
import { getGuestSearchInternalSecret } from "@/lib/server/guest-search-secret";

export async function GET(req: NextRequest) {
  const secret = getGuestSearchInternalSecret();
  if (!secret) {
    return NextResponse.json({ detail: "Гостьовий пошук тимчасово недоступний" }, { status: 503 });
  }

  const origin = req.headers.get("origin");
  const host = req.headers.get("host");
  if (!isAllowedGuestSearchRequest(origin, host)) {
    return NextResponse.json({ detail: "Forbidden" }, { status: 403 });
  }

  const token = issueGuestSearchToken(secret);
  const secure = process.env.NODE_ENV === "production";
  const res = NextResponse.json({ ok: true });
  res.cookies.set(GUEST_SEARCH_COOKIE, token, guestSearchCookieOptions(secure));
  return res;
}
