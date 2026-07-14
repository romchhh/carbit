"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { IconPlus } from "@/components/icons";
import { Button } from "@/components/ui/Button";
import {
  AppEmpty,
  AppLoading,
  AppPage,
} from "@/components/layout/AppPage";
import { MonitorSearchCard } from "@/components/search/MonitorSearchCard";
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
            <MonitorSearchCard key={s.id} search={s} />
          ))}
        </div>
      )}
    </AppPage>
  );
}
