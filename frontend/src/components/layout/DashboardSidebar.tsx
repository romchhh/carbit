"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { LogoIcon } from "@/components/brand/LogoIcon";
import { primaryNav, secondaryNav, type NavBadgeKey } from "@/lib/dashboard-nav";
import { notifications as notificationsApi, favorites as favoritesApi } from "@/lib/api";

type Props = {
  searchesUsed: number;
  searchesLimit: number;
};

export function DashboardSidebar({ searchesUsed, searchesLimit }: Props) {
  const pathname = usePathname();
  const pct = searchesLimit > 0 ? Math.round((searchesUsed / searchesLimit) * 100) : 0;
  const [badges, setBadges] = useState<Record<NavBadgeKey, number>>({ favorites: 0, notifications: 0 });

  useEffect(() => {
    Promise.all([
      favoritesApi.list().then(f => f.length).catch(() => 0),
      notificationsApi.stats().then(s => s.unread).catch(() => 0),
    ]).then(([favorites, notifications]) => setBadges({ favorites, notifications }));
  }, [pathname]);

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  return (
    <aside className="hidden w-[252px] shrink-0 lg:sticky lg:top-0 lg:block lg:self-start">
      <div className="flex h-[calc(100dvh-1.5rem)] max-h-[calc(100dvh-1.5rem)] flex-col overflow-hidden rounded-[28px] border border-border/50 bg-white shadow-island sm:h-[calc(100dvh-2rem)] sm:max-h-[calc(100dvh-2rem)] lg:h-[calc(100vh-2.5rem)] lg:max-h-[calc(100vh-2.5rem)]">
        <div className="border-b border-border/50 px-5 py-5">
          <Link href="/app/dashboard" className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-ink text-white shadow-sm">
              <LogoIcon size={20} light />
            </span>
            <div>
              <div className="text-[16px] font-bold tracking-tight text-ink">Carbit</div>
              <div className="text-[11px] text-muted">Особистий кабінет</div>
            </div>
          </Link>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {primaryNav.map(({ href, icon: Icon, label, badgeKey, badgeAccent }) => {
            const badge = badgeKey ? badges[badgeKey] : 0;
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] transition-all",
                  active
                    ? "bg-emerald/10 font-semibold text-emerald-dark shadow-sm"
                    : "text-muted hover:bg-surface hover:text-ink",
                )}
              >
                <Icon size={16} className={active ? "text-emerald-dark" : ""} />
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

          {secondaryNav.map(({ href, icon: Icon, label }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] transition-all",
                  active
                    ? "bg-emerald/10 font-semibold text-emerald-dark"
                    : "text-muted hover:bg-surface hover:text-ink",
                )}
              >
                <Icon size={16} />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-border/50 p-4">
          <div className="rounded-2xl bg-surface p-4">
            <div className="mb-2 flex justify-between text-[12px]">
              <span className="text-muted">Запити</span>
              <span className="font-semibold text-ink">
                {searchesUsed}/{searchesLimit}
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-border">
              <div
                className="h-full rounded-full bg-emerald transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            <Link
              href="/app/billing"
              className="mt-3 block text-[11px] font-semibold text-emerald-dark hover:underline"
            >
              Збільшити ліміт →
            </Link>
          </div>
        </div>
      </div>
    </aside>
  );
}

export function useDashboardBadges() {
  const pathname = usePathname();
  const [badges, setBadges] = useState<Record<NavBadgeKey, number>>({ favorites: 0, notifications: 0 });

  useEffect(() => {
    Promise.all([
      favoritesApi.list().then(f => f.length).catch(() => 0),
      notificationsApi.stats().then(s => s.unread).catch(() => 0),
    ]).then(([favorites, notifications]) => setBadges({ favorites, notifications }));
  }, [pathname]);

  return badges;
}
