"use client";

import { useEffect } from "react";

function isAppleBrowser() {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  return (
    /iPad|iPhone|iPod/.test(ua) ||
    (navigator.vendor?.includes("Apple") &&
      !/CriOS|FxiOS|EdgiOS|OPiOS/.test(ua))
  );
}

/** Safari service workers often cause stale cache and UI jank — unregister on load. */
export function SafariSwCleanup() {
  useEffect(() => {
    if (!isAppleBrowser() || !("serviceWorker" in navigator)) return;

    void navigator.serviceWorker.getRegistrations().then((regs) => {
      void Promise.all(regs.map((r) => r.unregister()));
    });

    if ("caches" in window) {
      void caches.keys().then((keys) => {
        void Promise.all(keys.map((k) => caches.delete(k)));
      });
    }
  }, []);

  return null;
}
