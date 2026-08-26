"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { adminApi, type AdminAnalytics, type AdminDashboard, type AdminTraffic } from "@/lib/admin-api";
import { AdminAreaChart, AdminBarChart, AdminStatusBadge } from "@/components/admin/AdminCharts";
import { PLAN_LABELS, cn } from "@/lib/utils";

const SOURCE_LABELS: Record<string, string> = {
  auto_ria: "AUTO.RIA",
  olx: "OLX",
  telegram: "Telegram",
};

export default function AdminDashboardPage() {
  const [data, setData] = useState<AdminDashboard | null>(null);
  const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null);
  const [traffic, setTraffic] = useState<AdminTraffic | null>(null);
  const [systemStatus, setSystemStatus] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      adminApi.dashboard(),
      adminApi.analytics(),
      adminApi.system(),
      adminApi.traffic(24, 7),
    ])
      .then(([dash, anal, sys, visitStats]) => {
        setData(dash);
        setAnalytics(anal);
        setSystemStatus(sys.scheduler_status);
        setTraffic(visitStats);
      })
      .catch(() => {});
  }, []);

  if (!data || !analytics) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-2 border-emerald border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const cards = [
    { label: "Клієнтів", value: data.total_users, sub: `+${data.new_users_today} сьогодні · +${data.new_users_week} за тиждень`, accent: data.new_users_today > 0 },
    { label: "MRR тарифів", value: `${data.revenue_month_uah.toLocaleString("uk-UA")} ₴`, sub: data.recurring_mrr_uah != null ? `LiqPay ${data.recurring_mrr_uah.toLocaleString("uk-UA")} ₴` : "оцінка за тарифами", accent: true },
    { label: "Платних", value: data.active_subscriptions, sub: `${data.trial_users} на trial`, accent: false },
    { label: "LiqPay active", value: data.liqpay_active ?? 0, sub: `${data.liqpay_past_due ?? 0} past due`, accent: (data.liqpay_past_due ?? 0) > 0 },
    { label: "Оголошень", value: analytics.total_listings, sub: `+${analytics.listings_today} сьогодні · ${analytics.duplicate_listings} дублів`, accent: analytics.listings_today > 0 },
    { label: "Пошуків", value: analytics.active_searches, sub: `${analytics.inactive_searches} неактивних`, accent: false },
    { label: "Закінчуються", value: data.expiring_7d ?? 0, sub: `${data.expired_plans ?? 0} уже прострочені`, accent: (data.expired_plans ?? 0) > 0 },
    { label: "Telegram", value: data.telegram_connected, sub: "підключено", accent: false },
  ];

  const maxChart = Math.max(...data.registrations_chart.map(c => c.count), 1);
  const totalBySource = Object.values(analytics.listings_by_source).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="max-w-[1200px]">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-black text-ink mb-1">Дашборд</h1>
          <p className="text-[13px] text-muted">Огляд платформи Carbit</p>
        </div>
        {systemStatus && (
          <div className="flex items-center gap-2 rounded-xl border border-border bg-white px-4 py-2.5">
            <span className="text-[12px] text-muted">Планувальник парсингу</span>
            <AdminStatusBadge status={systemStatus} />
          </div>
        )}
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map(({ label, value, sub, accent }) => (
          <div key={label} className="bg-white border border-border rounded-xl p-5">
            <div className="text-[12px] text-muted mb-2">{label}</div>
            <div className="text-[26px] font-black text-ink leading-none">{value}</div>
            <div className={cn("text-[11px] mt-1.5", accent ? "text-emerald-dark font-semibold" : "text-muted")}>{sub}</div>
          </div>
        ))}
      </div>

      <div className="mb-8 grid gap-6 lg:grid-cols-3">
        <div className="bg-white border border-border rounded-xl p-6 lg:col-span-1">
          <h2 className="text-[15px] font-bold text-ink mb-5">Джерела оголошень</h2>
          <div className="space-y-3">
            {Object.entries(analytics.listings_by_source).map(([source, count]) => (
              <div key={source} className="flex items-center gap-3">
                <span className="text-[13px] text-ink w-24 shrink-0">{SOURCE_LABELS[source] ?? source}</span>
                <div className="flex-1 h-2 bg-surface rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald rounded-full"
                    style={{ width: `${(count / totalBySource) * 100}%` }}
                  />
                </div>
                <span className="text-[13px] font-semibold text-ink w-12 text-right">{count}</span>
              </div>
            ))}
          </div>
          <Link href="/admin/listings" className="mt-4 inline-block text-[12px] font-semibold text-emerald hover:underline">
            Переглянути базу →
          </Link>
        </div>

        <div className="bg-white border border-border rounded-xl p-6 lg:col-span-2">
          <h2 className="text-[15px] font-bold text-ink mb-5">Нові оголошення (7 днів)</h2>
          <AdminBarChart data={analytics.listings_chart} />
        </div>
      </div>

      {analytics.data_quality && (
        <div className="mb-8 bg-white border border-border rounded-xl p-6">
          <h2 className="text-[15px] font-bold text-ink mb-2">Якість даних по джерелах</h2>
          <p className="text-[12px] text-muted mb-5">
            Частка оголошень з валідним published_at, VIN і ціною
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b border-border text-muted">
                  <th className="py-2 pr-4 font-medium">Джерело</th>
                  <th className="py-2 pr-4 font-medium">Всього</th>
                  <th className="py-2 pr-4 font-medium">published_at</th>
                  <th className="py-2 pr-4 font-medium">VIN</th>
                  <th className="py-2 font-medium">Ціна</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(analytics.data_quality).map(([source, row]) => (
                  <tr key={source} className="border-b border-border/60">
                    <td className="py-2.5 pr-4 font-medium text-ink">
                      {SOURCE_LABELS[source] ?? source}
                    </td>
                    <td className="py-2.5 pr-4 text-muted">{row.total}</td>
                    <td className="py-2.5 pr-4">{row.pct_published_at}%</td>
                    <td className="py-2.5 pr-4">{row.pct_vin}%</td>
                    <td className="py-2.5">{row.pct_price}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white border border-border rounded-xl p-6">
          <h2 className="text-[15px] font-bold text-ink mb-5">Реєстрації (7 днів)</h2>
          <div className="flex items-end gap-2 h-32">
            {data.registrations_chart.map(({ date, count }) => (
              <div key={date} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-emerald rounded-t-md transition-all min-h-[4px]"
                  style={{ height: `${(count / maxChart) * 100}%` }}
                />
                <span className="text-[10px] text-muted">{date}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border border-border rounded-xl p-6">
          <h2 className="text-[15px] font-bold text-ink mb-5">Сповіщення (7 днів)</h2>
          <AdminBarChart data={analytics.notifications_chart} colorClass="bg-blue-500" />
        </div>
      </div>

      {traffic ? (
        <div className="mb-8 rounded-xl border border-border bg-white p-6">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-[15px] font-bold text-ink">Відвідування сайту</h2>
              <p className="text-[12px] text-muted">
                {traffic.online_now} онлайн · {traffic.today_total} сьогодні · {traffic.period_total} за 7 днів
              </p>
            </div>
            <Link href="/admin/traffic" className="text-[12px] font-semibold text-emerald hover:underline">
              Детальна аналітика →
            </Link>
          </div>
          <AdminAreaChart data={traffic.hourly_chart} height={150} />
        </div>
      ) : null}

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white border border-border rounded-xl p-6">
          <h2 className="text-[15px] font-bold text-ink mb-5">Розподіл тарифів</h2>
          <div className="space-y-3">
            {Object.entries(data.plan_breakdown).map(([plan, count]) => (
              <div key={plan} className="flex items-center gap-3">
                <span className="text-[13px] text-ink w-24 shrink-0">{PLAN_LABELS[plan] ?? plan}</span>
                <div className="flex-1 h-2 bg-surface rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald rounded-full"
                    style={{ width: `${data.total_users ? (count / data.total_users) * 100 : 0}%` }}
                  />
                </div>
                <span className="text-[13px] font-semibold text-ink w-8 text-right">{count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border border-border rounded-xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-[15px] font-bold text-ink">Парсинг (7 днів)</h2>
            <Link href="/admin/parsing" className="text-[12px] font-semibold text-emerald hover:underline">
              Керування →
            </Link>
          </div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {analytics.parse_runs_chart.map(row => (
              <div key={row.date} className="flex items-center justify-between text-[12px] rounded-lg bg-surface/60 px-3 py-2">
                <span className="font-medium text-ink">{row.date}</span>
                <span className="text-muted">
                  {row.runs} запусків · знайдено {row.listings_found} · нових {row.listings_new}
                </span>
                <span className={cn(
                  "font-semibold",
                  row.failed > 0 ? "text-red-600" : "text-emerald-dark",
                )}>
                  {row.failed > 0 ? `${row.failed} помилок` : row.success > 0 ? "OK" : "—"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <Link href="/admin/finance" className="rounded-full border border-border bg-white px-4 py-2 text-[13px] font-semibold hover:bg-surface">
          Фінанси / платежі
        </Link>
        <Link href="/admin/system" className="rounded-full border border-border bg-white px-4 py-2 text-[13px] font-semibold hover:bg-surface">
          Стан системи
        </Link>
        <Link href="/admin/parsing" className="rounded-full border border-border bg-white px-4 py-2 text-[13px] font-semibold hover:bg-surface">
          Запустити парсинг
        </Link>
      </div>
    </div>
  );
}
