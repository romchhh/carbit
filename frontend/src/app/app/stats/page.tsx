"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AppLoading } from "@/components/layout/AppPage";

/** Статистика перенесена в профіль (/app/account). */
export default function StatsPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/app/account");
  }, [router]);

  return <AppLoading />;
}
