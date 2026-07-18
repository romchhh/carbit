"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { primaryNav, secondaryNav, type NavBadgeKey } from "@/lib/dashboard-nav";
import { NOTIFICATIONS_CHANGED_EVENT } from "@/lib/notifications-events";
import { notifications as notificationsApi, searches as searchesApi } from "@/lib/api";
import { SubscriptionPitch } from "@/components/billing/SubscriptionPitch";

type Props = {
  searchesUsed: number;
  searchesLimit: number;
  planId: string;
  isTrial?: boolean;
};

function useNavBadges(): Record<NavBadgeKey, number> {
  const pathname = usePathname();
  const [badges, setBadges] = useState<Record<NavBadgeKey, number>>({
    notifications: 0,
    monitors: 0,
  });

  useEffect(() => {
    const refreshBadges = () => {
      Promise.all([
        notificationsApi.stats().then(s => s.unread).catch(() => 0),
        searchesApi
          .list()
          .then(items => items.reduce((sum, s) => sum + (s.new_count || 0), 0))
          .catch(() => 0),
      ]).then(([notifications, monitors]) => {
        // While on Alerts, hide the badge immediately (page marks all read).
        const onNotifications =
          pathname === "/app/notifications" || pathname.startsWith("/app/notifications/");
        setBadges({
          notifications: onNotifications ? 0 : notifications,
          monitors,
        });
      });
    };

    refreshBadges();
    window.addEventListener(NOTIFICATIONS_CHANGED_EVENT, refreshBadges);
    return () => {
      window.removeEventListener(NOTIFICATIONS_CHANGED_EVENT, refreshBadges);
    };
  }, [pathname]);

  return badges;
}

export function DashboardSidebar({ searchesUsed, searchesLimit, planId, isTrial }: Props) {
  const pathname = usePathname();
  const badges = useNavBadges();

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  return (
    <aside className="hidden w-[252px] shrink-0 lg:sticky lg:top-0 lg:block lg:self-start">
      <div className="flex h-[calc(100dvh-1.5rem)] max-h-[calc(100dvh-1.5rem)] flex-col overflow-hidden rounded-[28px] border border-border/50 bg-white shadow-island sm:h-[calc(100dvh-2rem)] sm:max-h-[calc(100dvh-2rem)] lg:h-[calc(100vh-2.5rem)] lg:max-h-[calc(100vh-2.5rem)]">
        <div className="border-b border-border/50 px-5 py-5">
          <Link href="/app/dashboard" className="block">
            <CarbitLogo variant="full" height={32} />
            <div className="mt-2 text-[11px] text-muted">Особистий кабінет</div>
          </Link>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {primaryNav.map(({ href, icon: Icon, label, badgeKey, badgeAccent, tourId }) => {
            const badge = badgeKey ? badges[badgeKey] : 0;
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                data-tour={tourId}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] text-ink transition-all",
                  active
                    ? "bg-surface font-semibold shadow-sm"
                    : "hover:bg-surface",
                )}
              >
                <Icon size={16} className="text-ink" />
                <span>{label}</span>
                {badge > 0 && (
                  <span
                    className={cn(
                      "ml-auto rounded-md px-1.5 py-0.5 text-[11px] font-semibold",
                      badgeAccent ? "bg-ink text-white" : "bg-surface text-muted",
                    )}
                  >
                    {badge}
                  </span>
                )}
              </Link>
            );
          })}

          <div className="!my-3 border-t border-border/60" />

          {secondaryNav.map(({ href, icon: Icon, label, tourId }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                data-tour={tourId}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] text-ink transition-all",
                  active ? "bg-surface font-semibold" : "hover:bg-surface",
                )}
              >
                <Icon size={16} className="text-ink" />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-border/50 p-4">
          <SubscriptionPitch
            variant="sidebar"
            planId={planId}
            searchesLimit={searchesLimit}
            searchesUsed={searchesUsed}
            isTrial={isTrial}
          />
        </div>
      </div>
    </aside>
  );
}

export function useDashboardBadges() {
  return useNavBadges();
}
