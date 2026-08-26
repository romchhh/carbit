"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { adminApi, type AdminTraffic, type AdminTrafficCalendarDay } from "@/lib/admin-api";
import {
  AdminAreaChart,
  AdminBarChart,
  AdminHeatmapHours,
  AdminHorizontalBars,
} from "@/components/admin/AdminCharts";
import { IconArrowLeft, IconArrowRight, IconX } from "@/components/icons";
import { formatKyivDateTime } from "@/lib/datetime";
import { cn } from "@/lib/utils";

type PeriodDays = 7 | 30;

const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"];

const MONTH_LABELS: Record<number, string> = {
  1: "Січень",
  2: "Лютий",
  3: "Березень",
  4: "Квітень",
  5: "Травень",
  6: "Червень",
  7: "Липень",
  8: "Серпень",
  9: "Вересень",
  10: "Жовтень",
  11: "Листопад",
  12: "Грудень",
};

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

function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1 + delta, 1));
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
}

function formatDayTitle(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return `${String(d).padStart(2, "0")}.${String(m).padStart(2, "0")}.${y}`;
}

function monthTitle(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return `${MONTH_LABELS[m] ?? month} ${y}`;
}

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
    <div className="rounded-2xl border border-border bg-white p-4 sm:p-5">
      <div className="flex items-center gap-2 text-[12px] text-muted">
        {pulse ? (
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald" />
          </span>
        ) : null}
        {label}
      </div>
      <div className={cn("mt-2 text-[26px] font-black leading-none sm:text-[30px]", accent ?? "text-ink")}>
        {value}
      </div>
      {sub ? <div className="mt-2 text-[11px] text-muted">{sub}</div> : null}
    </div>
  );
}

function TrafficCalendar({
  month,
  days,
  selectedDate,
  onMonthChange,
  onSelectDay,
}: {
  month: string;
  days: AdminTrafficCalendarDay[];
  selectedDate: string | null;
  onMonthChange: (month: string) => void;
  onSelectDay: (date: string | null) => void;
}) {
  const maxTotal = Math.max(...days.map(d => d.total), 1);
  const [year, monthNum] = month.split("-").map(Number);
  const firstWeekday = (new Date(Date.UTC(year, monthNum - 1, 1)).getUTCDay() + 6) % 7;
  const leading = Array.from({ length: firstWeekday }, (_, i) => i);

  const intensity = (total: number) => {
    if (total <= 0) return "bg-surface text-muted";
    const ratio = total / maxTotal;
    if (ratio >= 0.75) return "bg-emerald text-white";
    if (ratio >= 0.45) return "bg-emerald/55 text-ink";
    if (ratio >= 0.2) return "bg-emerald/25 text-ink";
    return "bg-emerald/10 text-ink";
  };

  return (
    <section className="rounded-2xl border border-border bg-white p-4 sm:p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-[16px] font-bold text-ink">Календар</h2>
          <p className="text-[12px] text-muted">Оберіть день, щоб побачити деталі</p>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            aria-label="Попередній місяць"
            onClick={() => onMonthChange(shiftMonth(month, -1))}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border text-ink hover:bg-surface"
          >
            <IconArrowLeft size={16} />
          </button>
          <div className="min-w-[132px] text-center text-[13px] font-semibold text-ink">
            {monthTitle(month)}
          </div>
          <button
            type="button"
            aria-label="Наступний місяць"
            onClick={() => onMonthChange(shiftMonth(month, 1))}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border text-ink hover:bg-surface"
          >
            <IconArrowRight size={16} />
          </button>
        </div>
      </div>

      <div className="mb-2 grid grid-cols-7 gap-1.5">
        {WEEKDAYS.map(day => (
          <div key={day} className="text-center text-[10px] font-semibold uppercase tracking-wide text-muted">
            {day}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1.5">
        {leading.map(i => (
          <div key={`pad-${i}`} className="aspect-square rounded-xl bg-transparent" />
        ))}
        {days.map(day => {
          const selected = selectedDate === day.date;
          const disabled = !day.selectable;
          return (
            <button
              key={day.date}
              type="button"
              disabled={disabled}
              onClick={() => onSelectDay(selected ? null : day.date)}
              title={`${formatDayTitle(day.date)}: ${day.total} переглядів · ${day.unique} унік.`}
              className={cn(
                "flex aspect-square flex-col items-center justify-center rounded-xl border text-[11px] transition-all",
                intensity(day.total),
                selected
                  ? "border-ink ring-2 ring-ink/20"
                  : "border-transparent hover:border-border",
                disabled && "cursor-not-allowed opacity-35",
              )}
            >
              <span className="font-bold">{Number(day.date.slice(-2))}</span>
              <span className={cn("text-[9px] font-semibold", day.total > 0 ? "opacity-90" : "opacity-40")}>
                {day.total || "·"}
              </span>
            </button>
          );
        })}
      </div>

      {selectedDate ? (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-emerald/25 bg-emerald/5 px-3 py-2.5">
          <div className="text-[12px] text-ink">
            Обрано <strong>{formatDayTitle(selectedDate)}</strong>
          </div>
          <button
            type="button"
            onClick={() => onSelectDay(null)}
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-semibold text-muted hover:bg-white hover:text-ink"
          >
            <IconX size={12} />
            Скинути
          </button>
        </div>
      ) : null}
    </section>
  );
}

export default function AdminTrafficPage() {
  const [data, setData] = useState<AdminTraffic | null>(null);
  const [loading, setLoading] = useState(true);
  const [periodDays, setPeriodDays] = useState<PeriodDays>(7);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [calendarMonth, setCalendarMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  });

  const load = useCallback(async () => {
    try {
      const report = await adminApi.traffic(24, periodDays, {
        date: selectedDate,
        month: calendarMonth,
      });
      setData(report);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [periodDays, selectedDate, calendarMonth]);

  useEffect(() => {
    setLoading(true);
    void load();
    const timer = setInterval(() => void load(), 30_000);
    return () => clearInterval(timer);
  }, [load]);

  const handleSelectDay = (date: string | null) => {
    setSelectedDate(date);
    if (date) {
      setCalendarMonth(date.slice(0, 7));
    }
  };

  const dailyChart = useMemo(
    () =>
      (data?.daily_chart ?? []).map(point => ({
        date: point.label,
        count: point.total,
      })),
    [data?.daily_chart],
  );

  if (loading && !data) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
      </div>
    );
  }

  const dayMode = Boolean(selectedDate);
  const dayLabel = selectedDate ? formatDayTitle(selectedDate) : null;

  return (
    <div className="max-w-[1180px]">
      <div className="mb-6 flex flex-col gap-4 sm:mb-8 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
        <div>
          <h1 className="mb-1 text-[24px] font-black text-ink sm:text-[28px]">Відвідування</h1>
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

      <div className="mb-6 grid gap-3 sm:mb-8 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
        <KpiCard
          label="Онлайн зараз"
          value={data?.online_now ?? 0}
          sub="активні за останні 5 хв"
          accent="text-emerald-dark"
          pulse={(data?.online_now ?? 0) > 0}
        />
        <KpiCard
          label={dayMode ? `День ${dayLabel}` : "Сьогодні"}
          value={dayMode ? (data?.selected_day_total ?? 0) : (data?.today_total ?? 0)}
          sub={`${dayMode ? (data?.selected_day_unique ?? 0) : (data?.today_unique ?? 0)} унікальних відвідувачів`}
        />
        <KpiCard
          label={`За ${periodDays} днів`}
          value={data?.period_total ?? 0}
          sub={`${data?.period_unique ?? 0} унікальних · ~${data?.avg_per_day ?? 0}/день`}
        />
        <KpiCard
          label={dayMode ? "Середнє / год" : "Остання година"}
          value={dayMode ? (data?.avg_per_hour ?? 0) : (data?.last_hour_total ?? 0)}
          sub={dayMode ? "за обраний день" : `~${data?.avg_per_hour ?? 0} переглядів/год`}
        />
      </div>

      <div className="mb-6 grid gap-6 xl:grid-cols-5">
        <div className="xl:col-span-2">
          <TrafficCalendar
            month={calendarMonth}
            days={data?.calendar ?? []}
            selectedDate={selectedDate}
            onMonthChange={setCalendarMonth}
            onSelectDay={handleSelectDay}
          />
        </div>

        <section className="rounded-2xl border border-border bg-white p-4 sm:p-6 xl:col-span-3">
          <div className="mb-4">
            <h2 className="text-[16px] font-bold text-ink">
              {dayMode ? `Динаміка за ${dayLabel}` : "Динаміка за 24 години"}
            </h2>
            <p className="text-[12px] text-muted">
              {dayMode ? "Перегляди по годинах обраного дня" : "Перегляди сторінок по годинах"}
            </p>
          </div>
          <AdminAreaChart data={data?.hourly_chart ?? []} showUnique />
        </section>
      </div>

      <div className="mb-6 grid gap-6 xl:grid-cols-5">
        <section className="rounded-2xl border border-border bg-white p-4 sm:p-6 xl:col-span-3">
          <h2 className="mb-1 text-[16px] font-bold text-ink">По днях</h2>
          <p className="mb-4 text-[12px] text-muted">Усього переглядів за обраний період</p>
          <AdminBarChart
            data={dailyChart}
            colorClass="bg-emerald"
            height={150}
            compact={periodDays >= 30}
          />
        </section>

        <section className="rounded-2xl border border-border bg-white p-4 sm:p-6 xl:col-span-2">
          <h2 className="mb-1 text-[16px] font-bold text-ink">Пристрої</h2>
          <p className="mb-4 text-[12px] text-muted">
            {dayMode ? `Розподіл за ${dayLabel}` : `Розподіл за ${periodDays} днів`}
          </p>
          <AdminHorizontalBars
            colorClass="bg-sky-500"
            rows={(data?.devices ?? []).map(row => ({
              label: DEVICE_LABELS[row.device] ?? row.device,
              count: row.count,
              share: (() => {
                const base = dayMode
                  ? (data?.selected_day_total ?? 0)
                  : (data?.period_total ?? 0);
                return base ? Math.round((row.count / base) * 1000) / 10 : 0;
              })(),
            }))}
            valueLabel={(count, share) => `${count}${share != null ? ` · ${share}%` : ""}`}
          />
        </section>
      </div>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-border bg-white p-4 sm:p-6">
          <h2 className="mb-1 text-[16px] font-bold text-ink">Географія</h2>
          <p className="mb-4 text-[12px] text-muted">
            {dayMode
              ? `Країни за ${dayLabel}`
              : "Топ країн за переглядами (визначення за IP)"}
          </p>
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

        <section className="rounded-2xl border border-border bg-white p-4 sm:p-6">
          <h2 className="mb-1 text-[16px] font-bold text-ink">Популярні сторінки</h2>
          <p className="mb-4 text-[12px] text-muted">
            {dayMode ? `Куди заходили ${dayLabel}` : "Куди заходять найчастіше"}
          </p>
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

      <section className="rounded-2xl border border-border bg-white p-4 sm:p-6">
        <h2 className="mb-1 text-[16px] font-bold text-ink">Активність по годинах доби</h2>
        <p className="mb-4 text-[12px] text-muted">
          {dayMode
            ? `Перегляди ${dayLabel} по годинах (за київським часом)`
            : `Сума переглядів за ${periodDays} днів, згрупована по годині (за київським часом)`}
        </p>
        <AdminHeatmapHours rows={data?.time_of_day ?? []} />
      </section>
    </div>
  );
}
