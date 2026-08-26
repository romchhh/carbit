"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { getApiUrl } from "@/lib/api-url";
import { detectVisitDevice, getVisitorId } from "@/lib/visit-id";

function shouldTrack(pathname: string): boolean {
  if (!pathname) return false;
  if (pathname.startsWith("/admin")) return false;
  if (pathname.startsWith("/api")) return false;
  return true;
}

export function VisitTracker() {
  const pathname = usePathname();
  const lastPath = useRef<string | null>(null);

  useEffect(() => {
    if (!pathname || !shouldTrack(pathname)) return;
    if (lastPath.current === pathname) return;
    lastPath.current = pathname;

    const visitorId = getVisitorId();
    if (!visitorId) return;

    const payload = JSON.stringify({
      path: pathname,
      visitor_id: visitorId,
      referrer: typeof document !== "undefined" ? document.referrer || null : null,
      device: detectVisitDevice(),
    });

    const url = `${getApiUrl()}/analytics/collect`;
    if (typeof navigator !== "undefined" && navigator.sendBeacon) {
      const blob = new Blob([payload], { type: "application/json" });
      if (navigator.sendBeacon(url, blob)) return;
    }

    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true,
      credentials: "omit",
    }).catch(() => {
      /* ignore */
    });
  }, [pathname]);

  return null;
}
