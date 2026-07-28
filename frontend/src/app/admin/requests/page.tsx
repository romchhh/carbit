"use client";

import { useCallback, useEffect, useState } from "react";
import { adminApi, type AdminApiUsage, type AdminApiUsageSource } from "@/lib/admin-api";
import { AdminBarChart } from "@/components/admin/AdminCharts";
import { formatKyivDateTime } from "@/lib/datetime";
import { cn } from "@/lib/utils";

type PeriodDays = 7 | 30;

const SOURCE_META: Record<
  string,
  { title: string; description: string; chartColor: string; accent: string }
> = {
  auto_ria: {
    title: "AUTO.RIA API",
    description: "Платні запити до developers.ria.com — пошук, деталі, фото, каталог",
    chartColor: "bg-blue-500",
    accent: "text-blue-700",
  },
  olx: {
    title: "OLX",
    description: "HTTP-запити до OLX: пошук, HTML-сторінки, деталі оголошень",
    chartColor: "bg-emerald",
    accent: "text-emerald-dark",
  },
  telegram_channels: {
    title: "Telegram (канали)",
    description: "Telethon: історія каналів, сканування та keyword-пошук",
    chartColor: "bg-sky-500",
    accent: "text-sky-700",
  },
  telegram_bot: {
    title: "Telegram Bot API",
    description: "Відправка повідомлень, медіа та webhook-виклики бота",
    chartColor: "bg-violet-500",
    accent: "text-violet-700",
  },
};

const OPERATION_LABELS: Record<string, string> = {
  search: "Пошук",
  info: "Деталі авто",
  fotos: "Фото",
  new_search: "Пошук нових",
  new_info: "Деталі нових",
  catalog: "Каталог марок/моделей",
  details: "Деталі оголошення",
  html: "HTML-сторінки",
  history: "Історія каналу",
  history_scan: "Скан історії",
  keyword_search: "Пошук за ключовими словами",
  sendMessage: "sendMessage",
  sendPhoto: "sendPhoto",
  sendMediaGroup: "sendMediaGroup",
  other: "Інше",
};

const SOURCE_ORDER = ["auto_ria", "olx", "telegram_channels", "telegram_bot"];

function operationLabel(op: string) {
  return OPERATION_LABELS[op] ?? op;
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

function SourceSection({
  sourceKey,
  data,
  days,
}: {
  sourceKey: string;
  data: AdminApiUsageSource;
  days: PeriodDays;
}) {
  const meta = SOURCE_META[sourceKey] ?? {
    title: sourceKey,
    description: "",
    chartColor: "bg-ink/60",
    accent: "text-ink",
  };

  const hourlyChart = data.hourly_chart.map(p => ({ date: p.label, count: p.total }));
  const dailyChart = data.daily_chart.map(p => ({ date: p.label, count: p.total }));
  const operations = data.operations_period?.length
    ? data.operations_period
    : data.operations_today;

  return (
    <section className="rounded-2xl border border-border bg-white p-6">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className={cn("text-[18px] font-bold", meta.accent)}>{meta.title}</h2>
          <p className="mt-1 text-[12px] text-muted max-w-xl">{meta.description}</p>
        </div>
        <div className="flex flex-wrap gap-3 text-[12px]">
          <div className="rounded-lg bg-surface/60 px-3 py-2">
            <div className="text-muted">За {days} днів</div>
            <div className="text-[18px] font-black text-ink">{data.period_total}</div>
          </div>
          <div className="rounded-lg bg-surface/60 px-3 py-2">
            <div className="text-muted">Сьогодні</div>
            <div className="text-[18px] font-black text-ink">{data.today_total}</div>
          </div>
          <div className="rounded-lg bg-surface/60 px-3 py-2">
            <div className="text-muted">Остання година</div>
            <div className="text-[18px] font-black text-ink">{data.last_hour_total}</div>
          </div>
          <div className="rounded-lg bg-surface/60 px-3 py-2">
            <div className="text-muted">Середньо / день</div>
            <div className="text-[18px] font-black text-ink">{data.avg_per_day}</div>
          </div>
        </div>
      </div>

      {data.period_err > 0 && (
        <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-[12px] text-red-600">
          Помилок за період: {data.period_err} з {data.period_total}
        </p>
      )}

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="text-[13px] font-semibold text-ink mb-3">Погодинно (24 год)</h3>
          <AdminBarChart data={hourlyChart} colorClass={meta.chartColor} height={140} />
        </div>
        <div>
          <h3 className="text-[13px] font-semibold text-ink mb-3">По днях ({days} днів)</h3>
          <AdminBarChart
            data={dailyChart}
            colorClass={meta.chartColor}
            height={140}
            compact={days >= 30}
          />
        </div>
      </div>

      {operations.length > 0 && (
        <div>
          <h3 className="text-[13px] font-semibold text-ink mb-3">
            Розбивка за {days} днів (на що йдуть запити)
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-border text-left text-muted">
                  <th className="pb-2 pr-4 font-medium">Операція</th>
                  <th className="pb-2 font-medium text-right">Кількість</th>
                </tr>
              </thead>
              <tbody>
                {operations.map(row => (
                  <tr key={row.operation} className="border-b border-border/50">
                    <td className="py-2.5 pr-4 text-ink">{operationLabel(row.operation)}</td>
                    <td className="py-2.5 text-right font-semibold tabular-nums">{row.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}

export default function AdminRequestsPage() {
  const [data, setData] = useState<AdminApiUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [periodDays, setPeriodDays] = useState<PeriodDays>(7);

  const load = useCallback(async () => {
    try {
      const report = await adminApi.apiUsage(24, periodDays);
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
    const timer = setInterval(load, 60_000);
    return () => clearInterval(timer);
  }, [load]);

  if (loading && !data) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
      </div>
    );
  }

  const totalPeriod = SOURCE_ORDER.reduce(
    (sum, key) => sum + (data?.sources[key]?.period_total ?? 0),
    0,
  );

  return (
    <div className="max-w-[1100px]">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-black text-ink mb-1">Запити</h1>
          <p className="text-[13px] text-muted">
            OLX, Telegram та AUTO.RIA API — кількість, періодичність і розподіл по операціях
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <PeriodToggle value={periodDays} onChange={setPeriodDays} />
          {data && (
            <div className="text-[11px] text-muted">
              Оновлено: {formatKyivDateTime(data.generated_at)}
            </div>
          )}
        </div>
      </div>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-border bg-white p-5 sm:col-span-2 lg:col-span-1">
          <div className="text-[12px] text-muted mb-2">Усього за {periodDays} днів</div>
          <div className="text-[28px] font-black text-ink">{totalPeriod}</div>
        </div>
        {SOURCE_ORDER.map(key => {
          const src = data?.sources[key];
          const meta = SOURCE_META[key];
          if (!src || !meta) return null;
          return (
            <div key={key} className="rounded-xl border border-border bg-white p-5">
              <div className="text-[12px] text-muted mb-2">{meta.title}</div>
              <div className={cn("text-[24px] font-black", meta.accent)}>{src.period_total}</div>
              <div className="mt-1 text-[11px] text-muted">
                {src.today_total} сьогодні · {src.last_hour_total} за останню год
              </div>
            </div>
          );
        })}
      </div>

      <div className="space-y-6">
        {SOURCE_ORDER.map(key =>
          data?.sources[key] ? (
            <SourceSection key={key} sourceKey={key} data={data.sources[key]} days={periodDays} />
          ) : null,
        )}
      </div>
    </div>
  );
}
