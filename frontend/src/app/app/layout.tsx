"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { DashboardSidebar, useDashboardBadges } from "@/components/layout/DashboardSidebar";
import { DashboardMobileNav } from "@/components/layout/DashboardMobileNav";
import { AppShellHeader } from "@/components/layout/AppShellHeader";
import { PublicListingShell } from "@/components/layout/PublicListingShell";
import { OnboardingTour } from "@/components/onboarding/OnboardingTour";
import { PwaInstallPrompt } from "@/components/pwa/PwaInstallPrompt";
import { PwaLoadingScreen } from "@/components/pwa/PwaLoadingScreen";
import { useAuth } from "@/contexts/AuthProvider";
import * as api from "@/lib/api";
import { completeOnboarding, shouldShowOnboarding } from "@/lib/onboarding";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loading, initialized, refreshUser } = useAuth();
  const [searchesUsed, setSearchesUsed] = useState(0);
  const [tourActive, setTourActive] = useState(false);
  const badges = useDashboardBadges();
  const isOnboardingRoute = pathname === "/app/onboarding";
  const isPublicListing = pathname.startsWith("/app/listing/");

  useEffect(() => {
    if (isPublicListing) return;
    if (!initialized || loading || user) return;
    // Hard redirect — soft replace знову потрапляє під middleware /app і зависає на лоадері
    const redirect = pathname.startsWith("/app") ? pathname : "/app/dashboard";
    window.location.replace(`/auth/login?redirect=${encodeURIComponent(redirect)}`);
  }, [initialized, loading, user, pathname, isPublicListing]);

  useEffect(() => {
    if (isOnboardingRoute) {
      router.replace("/app/dashboard");
    }
  }, [isOnboardingRoute, router]);

  useEffect(() => {
    if (!user || isOnboardingRoute || isPublicListing) return;
    api.searches.list()
      .then(searches => setSearchesUsed(searches.filter(s => s.is_active).length))
      .catch(() => setSearchesUsed(0));
  }, [user, isOnboardingRoute, isPublicListing]);

  useEffect(() => {
    if (!user || tourActive || !shouldShowOnboarding(user)) return;
    if (pathname !== "/app/dashboard") return;
    const timer = window.setTimeout(() => setTourActive(true), 500);
    return () => window.clearTimeout(timer);
  }, [user, pathname, tourActive]);

  const finishOnboarding = async () => {
    try {
      await api.users.completeOnboarding();
    } catch {
      /* ignore */
    }
    completeOnboarding();
    setTourActive(false);
    void refreshUser();
  };

  if (isPublicListing) {
    if (!initialized || loading) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-white">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
        </div>
      );
    }
    if (!user) {
      return <PublicListingShell>{children}</PublicListingShell>;
    }
  }

  if (!initialized || loading || !user) {
    return (
      <div className="app-pwa-root flex min-h-0 flex-col overflow-hidden bg-white">
        <div className="app-pwa-statusbar lg:hidden" aria-hidden />
        <PwaLoadingScreen fixed={false} className="relative min-h-0 flex-1 bg-white" />
      </div>
    );
  }

  if (isOnboardingRoute) {
    return (
      <div className="app-pwa-root flex min-h-0 flex-col overflow-hidden bg-white">
        <PwaLoadingScreen fixed={false} className="relative min-h-0 flex-1 bg-white" />
      </div>
    );
  }

  const firstName = user.name.split(" ")[0];

  return (
    <div className="app-pwa-root flex min-h-0 flex-col overflow-hidden bg-white lg:relative lg:min-h-screen lg:h-screen lg:bg-canvas">
      <div className="app-pwa-statusbar lg:hidden" aria-hidden />
      <AppShellHeader unreadNotifications={badges.notifications} />

      <div className="mx-auto flex min-h-0 w-full max-w-[1440px] flex-1 flex-col overflow-hidden lg:px-6 lg:py-5">
        <div className="flex min-h-0 flex-1 gap-4 overflow-hidden lg:items-start lg:gap-5">
          <DashboardSidebar searchesUsed={searchesUsed} searchesLimit={user.searches_limit} />

          <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden lg:h-[calc(100vh-2.5rem)]">
            <div className="app-mobile-shell flex min-h-0 flex-1 flex-col overflow-hidden bg-[#eef0f4] lg:rounded-[28px] lg:border lg:border-border/50 lg:bg-white lg:shadow-island">
              <div className="app-mobile-scroll min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-4 pb-[var(--mobile-nav-height)] pt-[var(--mobile-header-offset)] sm:px-6 lg:px-12 lg:pb-8 lg:pt-8">
                <div className="app-mobile-content mx-auto flex w-full max-w-[980px] flex-col">
                  {children}

                  <div className="mt-5 lg:mt-6">
                    <PwaInstallPrompt />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <DashboardMobileNav badges={badges} />

      {tourActive && (
        <OnboardingTour
          firstName={firstName}
          onComplete={() => void finishOnboarding()}
          onSkip={() => void finishOnboarding()}
        />
      )}
    </div>
  );
}
