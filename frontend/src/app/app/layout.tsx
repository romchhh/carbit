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
    return (
      <div className="app-pwa-root flex min-h-0 flex-col overflow-hidden bg-white">
        <div className="app-pwa-statusbar lg:hidden" aria-hidden />
        <PwaLoadingScreen fixed={false} className="relative min-h-0 flex-1 bg-white" />
      </div>
    );
  }

  if (isOnboarding) {
    return <>{children}</>;
  }

  return (
      <div className="app-pwa-root flex min-h-0 flex-col overflow-hidden bg-white lg:relative lg:min-h-screen lg:h-screen lg:bg-canvas">
      <div className="app-pwa-statusbar lg:hidden" aria-hidden />

      <div className="mx-auto flex min-h-0 w-full max-w-[1440px] flex-1 flex-col overflow-hidden lg:px-6 lg:py-5">
        <div className="flex min-h-0 flex-1 gap-4 overflow-hidden lg:items-start lg:gap-5">
          <DashboardSidebar searchesUsed={searchesUsed} searchesLimit={user.searches_limit} />

          <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden lg:h-[calc(100vh-2.5rem)]">
            <div className="app-mobile-shell flex min-h-0 flex-1 flex-col overflow-hidden bg-white lg:rounded-[28px] lg:border lg:border-border/50 lg:shadow-island">
              <div className="app-mobile-scroll min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-4 py-4 pb-[var(--mobile-nav-height)] sm:px-6 sm:py-6 lg:px-12 lg:py-8 lg:pb-8">
                <div className="app-mobile-content mx-auto flex w-full max-w-[980px] flex-col">
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
