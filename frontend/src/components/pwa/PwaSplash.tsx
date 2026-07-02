"use client";

import { useEffect, useState } from "react";
import { PwaLoadingScreen } from "@/components/pwa/PwaLoadingScreen";
import { cn } from "@/lib/utils";

/** Splash лише на першому завантаженні — без manual DOM .remove() (ламає React при навігації). */
export function PwaSplash() {
  const [hidden, setHidden] = useState(false);
  const [mounted, setMounted] = useState(true);

  useEffect(() => {
    const hide = () => {
      setHidden(true);
      window.setTimeout(() => setMounted(false), 320);
    };

    if (document.readyState === "complete") {
      requestAnimationFrame(hide);
    } else {
      window.addEventListener("load", hide, { once: true });
    }

    const fallback = window.setTimeout(hide, 2200);
    return () => window.clearTimeout(fallback);
  }, []);

  if (!mounted) return null;

  return (
    <div className="app-pwa-root fixed inset-0 z-[9999] flex flex-col">
      <div className="app-pwa-statusbar lg:hidden" aria-hidden />
      <PwaLoadingScreen
        fixed={false}
        className={cn(
          "min-h-0 flex-1 transition-opacity duration-300 ease-out",
          hidden && "pointer-events-none opacity-0",
        )}
        aria-hidden={hidden}
      />
    </div>
  );
}
