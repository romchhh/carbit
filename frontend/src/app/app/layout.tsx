"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { DashboardSidebar, useDashboardBadges } from "@/components/layout/DashboardSidebar";
import { DashboardMobileNav } from "@/components/layout/DashboardMobileNav";
import { AppShellHeader } from "@/components/layout/AppShellHeader";
import { PwaInstallPrompt } from "@/components/pwa/PwaInstallPrompt";
import { PwaLoadingScreen } from "@/components/pwa/PwaLoadingScreen";
import { useAuth } from "@/contexts/AuthProvider";
import * as api from "@/lib/api";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loading, initialized } = useAuth();
  const [searchesUsed, setSearchesUsed] = useState(0);
  const badges = useDashboardBadges();
  const isOnboarding = pathname === "/app/onboarding";

  useEffect(() => {
    if (!initialized || loading || user) return;
    const redirect = pathname.startsWith("/app") ? pathname : "/app/dashboard";
    router.replace(`/auth/login?redirect=${encodeURIComponent(redirect)}`);
  }, [initialized, loading, user, pathname, router]);

  useEffect(() => {
    if (!user || isOnboarding) return;
    api.searches.list()
      .then(searches => setSearchesUsed(searches.filter(s => s.is_active).length))
      .catch(() => setSearchesUsed(0));
  }, [user, isOnboarding]);

  if (!initialized || loading || !user) {
    return <PwaLoadingScreen fixed={false} />;
  }

  if (isOnboarding) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-[100dvh] bg-white lg:min-h-screen lg:bg-canvas lg:h-screen lg:overflow-hidden">
      <div className="mx-auto h-full max-w-[1440px] lg:px-6 lg:py-5">
        <div className="flex h-full gap-4 lg:gap-5 lg:items-start">
          <DashboardSidebar searchesUsed={searchesUsed} searchesLimit={user.searches_limit} />

          <div className="min-h-0 min-w-0 flex-1 lg:h-[calc(100vh-2.5rem)]">
            <div className="flex h-[100dvh] min-h-[100dvh] w-full flex-col overflow-hidden bg-white lg:h-full lg:min-h-0 lg:rounded-[28px] lg:border lg:border-border/50 lg:shadow-island">
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
