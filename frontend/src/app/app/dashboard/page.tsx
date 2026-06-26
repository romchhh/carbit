"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { IconPlus, IconZap, IconArrowRight } from "@/components/icons";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthProvider";
import { searches as searchesApi, users as usersApi } from "@/lib/api";
import {
  AppEmpty,
  AppLoading,
  AppPage,
  AppSection,
  AppStatCard,
  AppStatGrid,
} from "@/components/layout/AppPage";
import type { SearchQuery, DashboardStats } from "@/types/api";

function formatSearchDesc(filters: Record<string, unknown>): string {
  const parts: string[] = [];
  if (filters.brand) parts.push(String(filters.brand));
  if (filters.model) parts.push(String(filters.model));
  if (filters.year_from || filters.year_to) {
    parts.push(`${filters.year_from ?? "…"}–${filters.year_to ?? "…"}`);
  }
  if (filters.price_to) parts.push(`до ${Number(filters.price_to).toLocaleString("uk-UA")} грн`);
  if (filters.region) parts.push(String(filters.region));
  return parts.length > 0 ? parts.join(" · ") : "Без фільтрів";
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [searches, setSearches] = useState<SearchQuery[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    searchesApi.list()
      .then(setSearches)
      .catch(() => setSearches([]))
      .finally(() => setLoading(false));
    usersApi.dashboard().then(setStats).catch(() => {});
  }, []);

  if (!user) return null;

  const activeCount = searches.filter(s => s.is_active).length;
  const limit = user.searches_limit;
  const remaining = Math.max(0, limit - activeCount);
  const totalNew = searches.reduce((sum, s) => sum + s.new_count, 0);

  const statsCards = stats ? [
    { label: "Активних", value: stats.active_searches, sub: `з ${stats.searches_limit}`, accent: false },
    { label: "Нових сьогодні", value: stats.new_listings_today, sub: `${stats.new_listings_yesterday} вчора`, accent: stats.new_listings_today > 0 },
    { label: "В обраному", value: stats.favorites_count, sub: "авто", accent: false },
    { label: "Сповіщень", value: stats.unread_notifications, sub: "непрочитаних", accent: stats.unread_notifications > 0 },
  ] : [
    { label: "Активних", value: activeCount, sub: `з ${limit}`, accent: false },
    { label: "Нових", value: totalNew, sub: "за добу", accent: totalNew > 0 },
    { label: "Запитів", value: searches.length, sub: "всього", accent: false },
    { label: "Джерел", value: "3", sub: "AUTO.RIA · OLX · TG", accent: false },
  ];

  return (
    <AppPage
      wide
      title="Мої пошуки"
      description={`Привіт, ${user.name.split(" ")[0]}! До ${limit} активних запитів одночасно.`}
      action={
        <Link href="/app/search">
          <Button variant="primary" size="md" className="gap-1.5">
            <IconPlus size={14} /> Новий запит
          </Button>
        </Link>
      }
    >
      <AppStatGrid className="mb-6">
        {statsCards.map(card => (
          <AppStatCard key={card.label} {...card} />
        ))}
      </AppStatGrid>

      {loading ? (
        <AppLoading />
      ) : searches.length === 0 ? (
        <AppEmpty>
          <p className="text-[15px] text-muted">Ще немає пошукових запитів</p>
          <p className="mx-auto mt-2 max-w-sm text-[13px] text-muted/80">
            Створіть перший — Carbit почне моніторити AUTO.RIA, OLX і Telegram.
          </p>
          <Link href="/app/search" className="mt-5 inline-block">
            <Button variant="primary" size="md" className="gap-1.5">
              <IconPlus size={14} /> Створити запит
            </Button>
          </Link>
        </AppEmpty>
      ) : (
        <div className="space-y-3">
          {searches.map(s => (
            <AppSection
              key={s.id}
              className={cn("!bg-white p-4 sm:p-5", !s.is_active && "opacity-60")}
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                <div className="flex min-w-0 flex-1 items-start gap-3">
                  <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", s.is_active ? "bg-emerald" : "bg-border")} />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-[15px] font-semibold text-ink">{s.name}</span>
                      {s.new_count > 0 && (
                        <Badge variant="ink" className="gap-1">
                          <IconZap size={9} /> {s.new_count}
                        </Badge>
                      )}
                    </div>
                    <p className="mt-1 truncate text-[12px] text-muted">{formatSearchDesc(s.filters)}</p>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-4 sm:justify-end">
                  <div className="text-left sm:text-right">
                    <div className={cn("text-[20px] font-black leading-none", s.is_active ? "text-emerald-dark" : "text-muted")}>
                      {s.is_active ? s.total_count : "—"}
                    </div>
                    <div className="mt-1 text-[10px] uppercase tracking-wide text-muted">знайдено</div>
                  </div>
                  {s.is_active && (
                    <Link
                      href={`/app/results?search=${s.id}`}
                      className="inline-flex items-center gap-1 rounded-xl bg-emerald/10 px-3 py-2 text-[12px] font-semibold text-emerald-dark transition-colors hover:bg-emerald/15"
                    >
                      Результати <IconArrowRight size={11} />
                    </Link>
                  )}
                </div>
              </div>
            </AppSection>
          ))}
        </div>
      )}

      {!loading && remaining > 0 && (
        <Link
          href="/app/search"
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-border/70 py-4 text-[13px] text-muted transition-colors hover:border-emerald/30 hover:bg-emerald/5 hover:text-ink"
        >
          <IconPlus size={14} /> Ще {remaining} {remaining === 1 ? "запит" : "запити"} доступно
        </Link>
      )}
    </AppPage>
  );
}
