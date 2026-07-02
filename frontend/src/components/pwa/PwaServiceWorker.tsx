"use client";

import { useEffect } from "react";
import { isStandalonePwa } from "@/lib/pwa";

const WORKBOX_CACHE_PREFIXES = ["workbox", "next-", "static-", "google-fonts", "apis", "cross-origin", "start-url", "others"];

function shouldClearCache(name: string) {
  if (name.startsWith("workbox")) return true;
  return WORKBOX_CACHE_PREFIXES.some(prefix => name === prefix || name.startsWith(prefix));
}

/** SW тільки у встановленому PWA; у звичайному браузері — без кешу, щоб не ламати Next.js навігацію. */
export function PwaServiceWorker() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    const standalone = isStandalonePwa();

    if (!standalone) {
      void navigator.serviceWorker.getRegistrations().then(regs =>
        Promise.all(regs.map(reg => reg.unregister())),
      );
      void caches.keys().then(keys =>
        Promise.all(keys.filter(shouldClearCache).map(key => caches.delete(key))),
      );
      return;
    }

    const workbox = (window as Window & { workbox?: { register: () => Promise<unknown> } }).workbox;
    if (workbox) {
      void workbox.register();
    }
  }, []);

  return null;
}
