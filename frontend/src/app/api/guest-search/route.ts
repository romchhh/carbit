import { NextRequest, NextResponse } from "next/server";
import { GUEST_SEARCH_COOKIE, verifyGuestSearchToken } from "@/lib/server/guest-search-token";
import {
  isAllowedGuestSearchRequest,
  isAllowedSecFetchSite,
} from "@/lib/server/guest-search-origin";
import { getGuestSearchInternalSecret } from "@/lib/server/guest-search-secret";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function backendOrigin(): string {
  const fromEnv = process.env.BACKEND_INTERNAL_URL?.trim();
  if (fromEnv) return fromEnv.replace(/\/$/, "");
  return process.env.NODE_ENV === "production" ? "http://backend:8000" : "http://localhost:8000";
}

function internalSecret(): string {
  return getGuestSearchInternalSecret();
}

export async function POST(req: NextRequest) {
  const secret = internalSecret();
  if (!secret) {
    return NextResponse.json({ detail: "Гостьовий пошук тимчасово недоступний" }, { status: 503 });
  }

  const origin = req.headers.get("origin");
  const host = req.headers.get("host");
  if (!isAllowedGuestSearchRequest(origin, host)) {
    return NextResponse.json({ detail: "Forbidden" }, { status: 403 });
  }

  if (!isAllowedSecFetchSite(req.headers.get("sec-fetch-site"))) {
    return NextResponse.json({ detail: "Forbidden" }, { status: 403 });
  }

  const cookie = req.cookies.get(GUEST_SEARCH_COOKIE)?.value;
  if (!verifyGuestSearchToken(secret, cookie)) {
    return NextResponse.json({ detail: "Guest session required" }, { status: 403 });
  }

  const qs = req.nextUrl.searchParams.toString();
  const url = `${backendOrigin()}/api/v1/searches/live/guest${qs ? `?${qs}` : ""}`;

  const headers = new Headers();
  headers.set("Content-Type", "application/json");
  headers.set("X-Internal-Secret", secret);

  const fwd = req.headers.get("x-forwarded-for");
  const realIp = req.headers.get("x-real-ip");
  if (fwd) headers.set("X-Forwarded-For", fwd);
  else if (realIp) headers.set("X-Real-IP", realIp);
  else if (host) headers.set("X-Forwarded-For", req.headers.get("x-forwarded-for") ?? "unknown");

  const ua = req.headers.get("user-agent");
  if (ua) headers.set("User-Agent", ua);

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: "POST",
      headers,
      body: await req.arrayBuffer(),
      cache: "no-store",
    });
  } catch (err) {
    console.error("[guest-search] upstream failed", url, err);
    return NextResponse.json({ detail: "API тимчасово недоступне" }, { status: 502 });
  }

  const outHeaders = new Headers();
  const contentType = upstream.headers.get("content-type");
  if (contentType) outHeaders.set("Content-Type", contentType);
  const retryAfter = upstream.headers.get("retry-after");
  if (retryAfter) outHeaders.set("Retry-After", retryAfter);

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: outHeaders,
  });
}
