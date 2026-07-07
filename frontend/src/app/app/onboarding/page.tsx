"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { PwaLoadingScreen } from "@/components/pwa/PwaLoadingScreen";

/** Старий маршрут — тур тепер на /app/dashboard */
export default function OnboardingRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/app/dashboard");
  }, [router]);

  return <PwaLoadingScreen fixed className="min-h-screen bg-white" />;
}
