"use client";

import { useEffect } from "react";
import { isStandalonePwa } from "@/lib/pwa";

function isAppleBrowser() {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  return (
    /iPad|iPhone|iPod/.test(ua) ||
    (navigator.vendor?.includes("Apple") &&
      !/CriOS|FxiOS|EdgiOS|OPiOS/.test(ua))
  );
}

/** In Safari tabs SW often causes stale cache — but keep it for installed PWA. */
export function SafariSwCleanup() {
  useEffect(() => {
    if (isStandalonePwa() || !isAppleBrowser() || !("serviceWorker" in navigator)) return;

    void navigator.serviceWorker.getRegistrations().then(regs => {
      void Promise.all(regs.map(r => r.unregister()));
    });

    if ("caches" in window) {
      void caches.keys().then(keys => {
        void Promise.all(keys.map(k => caches.delete(k)));
      });
    }
  }, []);

  return null;
}
