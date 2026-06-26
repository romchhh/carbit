"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { DashboardSidebar, useDashboardBadges } from "@/components/layout/DashboardSidebar";
import { DashboardMobileNav } from "@/components/layout/DashboardMobileNav";
import { AppShellHeader } from "@/components/layout/AppShellHeader";
import { PwaInstallPrompt } from "@/components/pwa/PwaInstallPrompt";
import { useAuth } from "@/contexts/AuthProvider";
import * as api from "@/lib/api";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, loading } = useAuth();
  const [searchesUsed, setSearchesUsed] = useState(0);
  const badges = useDashboardBadges();
  const isOnboarding = pathname === "/app/onboarding";

  useEffect(() => {
    if (!user || isOnboarding) return;
    api.searches.list()
      .then(searches => setSearchesUsed(searches.filter(s => s.is_active).length))
      .catch(() => setSearchesUsed(0));
  }, [user, isOnboarding]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
      </div>
    );
  }

  if (!user) return null;

  if (isOnboarding) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-canvas lg:h-screen lg:overflow-hidden">
      <div className="mx-auto h-full max-w-[1440px] px-3 py-3 sm:px-4 sm:py-4 lg:px-6 lg:py-5">
        <div className="flex h-full gap-4 lg:gap-5 lg:items-start">
          <DashboardSidebar searchesUsed={searchesUsed} searchesLimit={user.searches_limit} />

          <div className="min-h-0 min-w-0 flex-1 lg:h-[calc(100vh-2.5rem)]">
            <div className="flex h-full min-h-[calc(100dvh-1.5rem)] flex-col overflow-hidden rounded-[28px] border border-border/50 bg-white shadow-island sm:min-h-[calc(100dvh-2rem)] lg:min-h-0">
              <div className="flex flex-1 flex-col overflow-y-auto px-4 py-4 pb-28 sm:px-6 sm:py-6 lg:px-12 lg:py-8 lg:pb-8">
                <div className="mx-auto flex w-full max-w-[980px] flex-col">
                  <AppShellHeader unreadNotifications={badges.notifications} />

                  <div className="mb-5 lg:mb-6">
                    <PwaInstallPrompt />
                  </div>

                  {children}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <DashboardMobileNav badges={badges} />
    </div>
  );
}
