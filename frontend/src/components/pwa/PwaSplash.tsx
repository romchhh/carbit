"use client";

import { useEffect, useState } from "react";
import { PwaLoadingScreen } from "@/components/pwa/PwaLoadingScreen";

export function PwaSplash() {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    document.getElementById("pwa-boot-splash")?.remove();

    const hide = () => setVisible(false);

    if (document.readyState === "complete") {
      requestAnimationFrame(hide);
    } else {
      window.addEventListener("load", hide, { once: true });
    }

    const fallback = window.setTimeout(hide, 2800);
    return () => window.clearTimeout(fallback);
  }, []);

  if (!visible) return null;
  return <PwaLoadingScreen />;
}
