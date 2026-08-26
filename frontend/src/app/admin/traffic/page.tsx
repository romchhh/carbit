"use client";

import { useCallback, useEffect, useState } from "react";
import { adminApi, type AdminTraffic } from "@/lib/admin-api";
import {
  AdminAreaChart,
  AdminBarChart,
  AdminHeatmapHours,
  AdminHorizontalBars,
} from "@/components/admin/AdminCharts";
import { formatKyivDateTime } from "@/lib/datetime";
import { cn } from "@/lib/utils";

type PeriodDays = 7 | 30;

function countryFlag(code: string): string {
  if (!code || code.length !== 2 || code === "XX") return "🌍";
  const upper = code.toUpperCase();
  return String.fromCodePoint(...[...upper].map(char => 0x1f1e6 - 65 + char.charCodeAt(0)));
}

const DEVICE_LABELS: Record<string, string> = {
  mobile: "Мобільні",
  tablet: "Планшети",
  desktop: "Десктоп",
  unknown: "Невідомо",
};

function PeriodToggle({
  value,
  onChange,
}: {
  value: PeriodDays;
  onChange: (days: PeriodDays) => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-border bg-white p-1">
      {([7, 30] as const).map(days => (
        <button
          key={days}
          type="button"
          onClick={() => onChange(days)}
          className={cn(
            "rounded-md px-3 py-1.5 text-[12px] font-semibold transition-colors",
            value === days ? "bg-ink text-white" : "text-muted hover:text-ink",
          )}
        >
          {days} днів
        </button>
      ))}
    </div>
  );
}

function KpiCard({
  label,
  value,
  sub,
  accent,
  pulse,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
  pulse?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-border bg-white p-5">
      <div className="flex items-center gap-2 text-[12px] text-muted">
        {pulse ? <span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald opacity-60" /><span className="relative inline-flex h-2 w-2 rounded-full bg-emerald" /></span> : null}
        {label}
      </div>
      <div className={cn("mt-2 text-[30px] font-black leading-none", accent ?? "text-ink")}>{value}</div>
      {sub ? <div className="mt-2 text-[11px] text-muted">{sub}</div> : null}
    </div>
  );
}

export default function AdminTrafficPage() {
  const [data, setData] = useState<AdminTraffic | null>(null);
  const [loading, setLoading] = useState(true);
  const [periodDays, setPeriodDays] = useState<PeriodDays>(7);

  const load = useCallback(async () => {
    try {
      const report = await adminApi.traffic(24, periodDays);
      setData(report);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [periodDays]);

  useEffect(() => {
    setLoading(true);
    load();
    const timer = setInterval(load, 30_000);
    return () => clearInterval(timer);
  }, [load]);

  if (loading && !data) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
      </div>
    );
  }

  const dailyChart = (data?.daily_chart ?? []).map(point => ({
    date: point.label,
    count: point.total,
  }));

  return (
    <div className="max-w-[1180px]">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="mb-1 text-[28px] font-black text-ink">Відвідування</h1>
          <p className="text-[13px] text-muted">
            Перегляди сайту, гео, активність по годинах і онлайн зараз
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <PeriodToggle value={periodDays} onChange={setPeriodDays} />
          {data ? (
            <div className="text-[11px] text-muted">
              Оновлено: {formatKyivDateTime(data.generated_at)}
            </div>
          ) : null}
        </div>
      </div>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Онлайн зараз"
          value={data?.online_now ?? 0}
          sub="активні за останні 5 хв"
          accent="text-emerald-dark"
          pulse={(data?.online_now ?? 0) > 0}
        />
        <KpiCard
          label="Сьогодні"
          value={data?.today_total ?? 0}
          sub={`${data?.today_unique ?? 0} унікальних відвідувачів`}
        />
        <KpiCard
          label={`За ${periodDays} днів`}
          value={data?.period_total ?? 0}
          sub={`${data?.period_unique ?? 0} унікальних · ~${data?.avg_per_day ?? 0}/день`}
        />
        <KpiCard
          label="Остання година"
          value={data?.last_hour_total ?? 0}
          sub={`~${data?.avg_per_hour ?? 0} переглядів/год`}
        />
      </div>

      <div className="mb-6 grid gap-6 xl:grid-cols-5">
        <section className="rounded-2xl border border-border bg-white p-6 xl:col-span-3">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-[16px] font-bold text-ink">Динаміка за 24 години</h2>
              <p className="text-[12px] text-muted">Перегляди сторінок по годинах</p>
            </div>
          </div>
          <AdminAreaChart data={data?.hourly_chart ?? []} showUnique />
        </section>

        <section className="rounded-2xl border border-border bg-white p-6 xl:col-span-2">
          <h2 className="mb-1 text-[16px] font-bold text-ink">Пристрої</h2>
          <p className="mb-4 text-[12px] text-muted">Розподіл за {periodDays} днів</p>
          <AdminHorizontalBars
            colorClass="bg-sky-500"
            rows={(data?.devices ?? []).map(row => ({
              label: DEVICE_LABELS[row.device] ?? row.device,
              count: row.count,
              share: data?.period_total
                ? Math.round((row.count / data.period_total) * 1000) / 10
                : 0,
            }))}
            valueLabel={(count, share) => `${count}${share != null ? ` · ${share}%` : ""}`}
          />
        </section>
      </div>

      <section className="mb-6 rounded-2xl border border-border bg-white p-6">
        <h2 className="mb-1 text-[16px] font-bold text-ink">По днях</h2>
        <p className="mb-4 text-[12px] text-muted">Усього переглядів за обраний період</p>
        <AdminBarChart
          data={dailyChart}
          colorClass="bg-emerald"
          height={150}
          compact={periodDays >= 30}
        />
      </section>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-border bg-white p-6">
          <h2 className="mb-1 text-[16px] font-bold text-ink">Географія</h2>
          <p className="mb-4 text-[12px] text-muted">Топ країн за переглядами (визначення за IP)</p>
          <AdminHorizontalBars
            rows={(data?.countries ?? []).map(row => ({
              label: `${countryFlag(row.code)} ${row.name}`,
              sublabel: row.code,
              count: row.count,
              share: row.share,
            }))}
            valueLabel={(count, share) => `${count} · ${share ?? 0}%`}
          />
        </section>

        <section className="rounded-2xl border border-border bg-white p-6">
          <h2 className="mb-1 text-[16px] font-bold text-ink">Популярні сторінки</h2>
          <p className="mb-4 text-[12px] text-muted">Куди заходять найчастіше</p>
          <AdminHorizontalBars
            colorClass="bg-violet-500"
            rows={(data?.top_pages ?? []).map(row => ({
              label: row.label,
              sublabel: row.path,
              count: row.count,
              share: row.share,
            }))}
            valueLabel={(count, share) => `${count} · ${share ?? 0}%`}
          />
        </section>
      </div>

      <section className="rounded-2xl border border-border bg-white p-6">
        <h2 className="mb-1 text-[16px] font-bold text-ink">Активність по годинах доби</h2>
        <p className="mb-4 text-[12px] text-muted">
          Сума переглядів за {periodDays} днів, згрупована по годині (за київським часом)
        </p>
        <AdminHeatmapHours rows={data?.time_of_day ?? []} />
      </section>
    </div>
  );
}
