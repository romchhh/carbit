"use client";

import { useEffect, useState } from "react";
import { users as usersApi } from "@/lib/api";
import type { DashboardStats } from "@/types/api";
import { PLAN_LABELS } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthProvider";
import { AppLoading, AppPage, AppSection, AppStatCard, AppStatGrid } from "@/components/layout/AppPage";

export default function StatsPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    usersApi.dashboard().then(setStats).catch(() => {});
  }, []);

  if (!stats) return <AppLoading />;

  const cards = [
    { label: "Активних", value: stats.active_searches, sub: `з ${stats.searches_limit}`, accent: false },
    { label: "Нових сьогодні", value: stats.new_listings_today, sub: `${stats.new_listings_yesterday} вчора`, accent: stats.new_listings_today > 0 },
    { label: "В обраному", value: stats.favorites_count, sub: "авто", accent: false },
    { label: "Непрочитаних", value: stats.unread_notifications, sub: "сповіщень", accent: stats.unread_notifications > 0 },
  ];

  return (
    <AppPage
      title="Статистика"
      description={`Тариф: ${PLAN_LABELS[stats.plan] ?? stats.plan}${stats.is_trial_active ? " · Trial" : ""}`}
    >
      <AppStatGrid className="mb-6">
        {cards.map(card => (
          <AppStatCard key={card.label} {...card} />
        ))}
      </AppStatGrid>

      <AppSection className="!bg-white">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wide text-muted">Акаунт</div>
            <div className="mt-1 text-[15px] font-semibold text-ink">{user?.name}</div>
          </div>
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wide text-muted">Ліміт запитів</div>
            <div className="mt-1 text-[15px] font-semibold text-ink">{stats.searches_limit}</div>
          </div>
        </div>
      </AppSection>
    </AppPage>
  );
}
