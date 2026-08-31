"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

declare global {
  interface Window {
    fbq?: (...args: unknown[]) => void;
  }
}

/** PageView при клієнтській навігації (перший — уже з init-скрипта). */
export function FacebookPixelPageView() {
  const pathname = usePathname();
  const isFirst = useRef(true);

  useEffect(() => {
    if (isFirst.current) {
      isFirst.current = false;
      return;
    }
    if (typeof window.fbq !== "function") return;
    window.fbq("track", "PageView");
  }, [pathname]);

  return null;
}
