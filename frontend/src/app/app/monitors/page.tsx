"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { IconPlus, IconZap, IconArrowRight } from "@/components/icons";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  AppEmpty,
  AppLoading,
  AppPage,
  AppSection,
} from "@/components/layout/AppPage";
import { formatSearchDesc } from "@/lib/format-search-desc";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthProvider";
import { searches as searchesApi } from "@/lib/api";
import type { SearchQuery } from "@/types/api";

export default function MonitorsPage() {
  const { user } = useAuth();
  const [searches, setSearches] = useState<SearchQuery[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    searchesApi
      .list()
      .then(setSearches)
      .catch(() => setSearches([]))
      .finally(() => setLoading(false));
  }, []);

  if (!user) return null;

  const activeCount = searches.filter(s => s.is_active).length;
  const remaining = Math.max(0, user.searches_limit - activeCount);
  const totalNew = searches.reduce((sum, s) => sum + (s.new_count || 0), 0);

  return (
    <AppPage>
      <div className="mb-6 flex items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-black tracking-tight text-ink sm:text-[26px]">
            Мої моніторинги
          </h1>
          <p className="mt-1 text-[13px] text-muted">
            {activeCount} активних
            {remaining > 0 ? ` · ще ${remaining} доступно` : " · ліміт використано"}
            {totalNew > 0 ? ` · ${totalNew} нових авто` : ""}
          </p>
        </div>
        <Link href="/app/dashboard" className="shrink-0">
          <Button variant="emerald" size="sm" className="gap-1.5">
            <IconPlus size={13} /> Новий
          </Button>
        </Link>
      </div>

      {loading ? (
        <AppLoading />
      ) : searches.length === 0 ? (
        <AppEmpty>
          <p className="text-[15px] font-medium text-ink">Поки немає моніторингів</p>
          <p className="mx-auto mt-2 max-w-sm text-[13px] text-muted">
            Зробіть пошук і натисніть «Зберегти» — поточні авто і всі нові з’являться тут.
          </p>
          <Link href="/app/dashboard" className="mt-4 inline-block">
            <Button variant="emerald" size="sm" className="gap-1.5">
              <IconPlus size={13} /> Налаштувати фільтри
            </Button>
          </Link>
        </AppEmpty>
      ) : (
        <div className="space-y-3">
          {searches.map(s => (
            <Link key={s.id} href={`/app/monitors/${s.id}`} className="block">
              <AppSection
                className={cn(
                  "!bg-white p-4 transition-colors hover:border-emerald/30 sm:p-5",
                  !s.is_active && "opacity-60",
                )}
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                  <div className="flex min-w-0 flex-1 items-start gap-3">
                    <span
                      className={cn(
                        "mt-1.5 h-2 w-2 shrink-0 rounded-full",
                        s.is_active ? "bg-emerald" : "bg-border",
                      )}
                    />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="truncate text-[15px] font-semibold text-ink">{s.name}</span>
                        {s.new_count > 0 && (
                          <Badge variant="ink" className="gap-1">
                            <IconZap size={9} /> {s.new_count} нові
                          </Badge>
                        )}
                      </div>
                      <p className="mt-1 truncate text-[12px] text-muted">
                        {formatSearchDesc(s.filters)}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-4 sm:justify-end">
                    <div className="text-left sm:text-right">
                      <div
                        className={cn(
                          "text-[20px] font-black leading-none",
                          s.is_active ? "text-emerald-dark" : "text-muted",
                        )}
                      >
                        {s.is_active ? s.total_count : "—"}
                      </div>
                      <div className="mt-1 text-[10px] uppercase tracking-wide text-muted">авто</div>
                    </div>
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald/10 px-3 py-2 text-[12px] font-semibold text-emerald-dark">
                      Відкрити <IconArrowRight size={11} />
                    </span>
                  </div>
                </div>
              </AppSection>
            </Link>
          ))}
        </div>
      )}
    </AppPage>
  );
}
