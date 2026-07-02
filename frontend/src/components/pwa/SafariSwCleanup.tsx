"use client";

import { useEffect } from "react";
import { isStandalonePwa } from "@/lib/pwa";

const CLEANUP_KEY = "carbit:safari-sw-cleanup";

function isAppleBrowser() {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  return (
    /iPad|iPhone|iPod/.test(ua) ||
    (navigator.vendor?.includes("Apple") &&
      !/CriOS|FxiOS|EdgiOS|OPiOS/.test(ua))
  );
}

/** У Safari (не PWA) один раз знімаємо старий SW — без wipe всього cache (ламає перший перехід у /app). */
export function SafariSwCleanup() {
  useEffect(() => {
    if (isStandalonePwa() || !isAppleBrowser() || !("serviceWorker" in navigator)) return;
    if (sessionStorage.getItem(CLEANUP_KEY)) return;

    sessionStorage.setItem(CLEANUP_KEY, "1");

    void navigator.serviceWorker.getRegistrations().then(regs => {
      if (!regs.length) return;
      void Promise.all(regs.map(r => r.unregister())).then(() => {
        window.location.reload();
      });
    });
  }, []);

  return null;
}
