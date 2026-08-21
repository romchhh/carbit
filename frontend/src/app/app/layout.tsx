"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useDashboardBadges } from "@/components/layout/DashboardSidebar";
import { DashboardTopNav } from "@/components/layout/DashboardTopNav";
import { DashboardMobileNav } from "@/components/layout/DashboardMobileNav";
import { AppShellHeader } from "@/components/layout/AppShellHeader";
import { PublicListingShell } from "@/components/layout/PublicListingShell";
import { OnboardingTour } from "@/components/onboarding/OnboardingTour";
import { PwaInstallPrompt } from "@/components/pwa/PwaInstallPrompt";
import { PwaLoadingScreen } from "@/components/pwa/PwaLoadingScreen";
import { CompareBar } from "@/components/listings/CompareBar";
import { InstagramFollowModal } from "@/components/social/InstagramFollowModal";
import { useAuth } from "@/contexts/AuthProvider";
import {
  markInstagramFollowPromptShown,
  shouldShowInstagramFollowPrompt,
} from "@/lib/instagram-follow-prompt";
import * as api from "@/lib/api";
import { completeOnboarding, ONBOARDING_TOUR_EVENT, shouldShowOnboarding } from "@/lib/onboarding";

function isNestedScrollable(node: HTMLElement, root: HTMLElement): boolean {
  let current: HTMLElement | null = node;
  while (current && current !== root) {
    const { overflowY } = window.getComputedStyle(current);
    if (
      (overflowY === "auto" || overflowY === "scroll" || overflowY === "overlay") &&
      current.scrollHeight > current.clientHeight + 1
    ) {
      return true;
    }
    current = current.parentElement;
  }
  return false;
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loading, initialized, refreshUser } = useAuth();
  const [tourActive, setTourActive] = useState(false);
  const [instagramPromptOpen, setInstagramPromptOpen] = useState(false);
  const badges = useDashboardBadges();
  const isOnboardingRoute = pathname === "/app/onboarding";
  const isPublicListing = pathname.startsWith("/app/listing/");
  const isPublicCompare = pathname === "/app/compare" || pathname.startsWith("/app/compare/");
  const isPublicAppRoute = isPublicListing || isPublicCompare;
  const rootRef = useRef<HTMLDivElement>(null);
  const mainScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isPublicAppRoute) return;
    if (!initialized || loading || user) return;
    // Hard redirect — soft replace знову потрапляє під middleware /app і зависає на лоадері
    const redirect = pathname.startsWith("/app") ? pathname : "/app/dashboard";
    window.location.replace(`/auth/login?redirect=${encodeURIComponent(redirect)}`);
  }, [initialized, loading, user, pathname, isPublicAppRoute]);

  useEffect(() => {
    void api.fx.rates().catch(() => {});
  }, []);

  useEffect(() => {
    if (isOnboardingRoute) {
      router.replace("/app/dashboard");
    }
  }, [isOnboardingRoute, router]);

  useEffect(() => {
    if (!user || isOnboardingRoute || isPublicListing) return;
    void api.searches.list().catch(() => {});
  }, [user, isOnboardingRoute, isPublicListing]);

  useEffect(() => {
    if (!user || tourActive || !shouldShowOnboarding(user)) return;
    // Примусовий повтор туру — одразу; перший вхід — зі стартової головної.
    const force =
      typeof window !== "undefined" &&
      sessionStorage.getItem("autoradar_force_tour") === "true";
    if (!force && pathname !== "/app/dashboard") return;
    const timer = window.setTimeout(() => setTourActive(true), force ? 120 : 500);
    return () => window.clearTimeout(timer);
  }, [user, pathname, tourActive]);

  useEffect(() => {
    const onStartTour = () => {
      if (!user) return;
      setTourActive(true);
    };
    window.addEventListener(ONBOARDING_TOUR_EVENT, onStartTour);
    return () => window.removeEventListener(ONBOARDING_TOUR_EVENT, onStartTour);
  }, [user]);

  useEffect(() => {
    if (!user || tourActive || isPublicListing || isOnboardingRoute) return;
    if (pathname !== "/app/dashboard") return;
    if (!shouldShowInstagramFollowPrompt()) return;

    const timer = window.setTimeout(() => {
      markInstagramFollowPromptShown();
      setInstagramPromptOpen(true);
    }, 1800);

    return () => window.clearTimeout(timer);
  }, [user, pathname, tourActive, isPublicListing, isOnboardingRoute]);

  // Сірий canvas / поля навколо острова не в overflow-y — прокидаємо wheel у контент.
  useEffect(() => {
    const root = rootRef.current;
    const scrollEl = mainScrollRef.current;
    if (!root || !scrollEl) return;

    const onWheel = (event: WheelEvent) => {
      if (event.ctrlKey || event.defaultPrevented) return;
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (scrollEl.contains(target)) return;
      if (isNestedScrollable(target as HTMLElement, root)) return;
      scrollEl.scrollTop += event.deltaY;
    };

    root.addEventListener("wheel", onWheel, { passive: true });
    return () => root.removeEventListener("wheel", onWheel);
  }, [user, isOnboardingRoute, isPublicListing]);

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

  if (isPublicAppRoute) {
    if (!initialized || loading) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-white">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
        </div>
      );
    }
    if (!user) {
      return (
        <>
          <PublicListingShell>{children}</PublicListingShell>
          {isPublicCompare && <CompareBar />}
        </>
      );
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
    <div
      ref={rootRef}
      className="app-pwa-root flex min-h-0 flex-col overflow-hidden bg-white lg:relative lg:min-h-screen lg:h-screen lg:bg-canvas"
    >
      <div className="app-pwa-statusbar lg:hidden" aria-hidden />
      <AppShellHeader />

      <div className="mx-auto flex min-h-0 w-full max-w-[1440px] flex-1 flex-col overflow-hidden lg:px-6 lg:py-5">
        <DashboardTopNav />

        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden lg:h-[calc(100vh-8.5rem)]">
          <div className="app-mobile-shell flex min-h-0 flex-1 flex-col overflow-hidden bg-[#eef0f4] lg:rounded-[28px] lg:border lg:border-border/50 lg:bg-white lg:shadow-island">
            <div
              ref={mainScrollRef}
              className="app-mobile-scroll min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-2.5 pb-[var(--mobile-nav-height)] pt-[var(--mobile-header-offset)] sm:px-4 lg:pl-3 lg:pr-5 lg:pb-8 lg:pt-4 xl:pl-4 xl:pr-7"
            >
              <div className="app-mobile-content flex w-full max-w-[980px] flex-col lg:mx-0 lg:max-w-none">
                {children}

                  <div className="mt-5 lg:mt-6">
                    <PwaInstallPrompt />
                  </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <DashboardMobileNav badges={badges} />
      <CompareBar />

      {tourActive && (
        <OnboardingTour
          firstName={firstName}
          onComplete={() => void finishOnboarding()}
          onSkip={() => void finishOnboarding()}
        />
      )}

      <InstagramFollowModal
        open={instagramPromptOpen}
        onClose={() => setInstagramPromptOpen(false)}
      />
    </div>
  );
}
