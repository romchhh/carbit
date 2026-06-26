"use client";

import { useEffect, useState } from "react";
import { adminApi, AdminDashboard } from "@/lib/admin-api";
import { PLAN_LABELS, cn } from "@/lib/utils";

export default function AdminDashboardPage() {
  const [data, setData] = useState<AdminDashboard | null>(null);

  useEffect(() => {
    adminApi.dashboard().then(setData).catch(() => {});
  }, []);

  if (!data) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-2 border-emerald border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const cards = [
    { label: "Клієнтів", value: data.total_users, sub: `+${data.new_users_today} сьогодні`, accent: data.new_users_today > 0 },
    { label: "MRR", value: `${data.revenue_month_uah.toLocaleString("uk-UA")} ₴`, sub: "місячний дохід", accent: true },
    { label: "Платних", value: data.active_subscriptions, sub: `${data.trial_users} на trial`, accent: false },
    { label: "Telegram", value: data.telegram_connected, sub: "підключено", accent: false },
    { label: "Пошуків", value: data.total_searches, sub: "активних запитів", accent: false },
    { label: "Сповіщень", value: data.total_notifications, sub: "всього надіслано", accent: false },
  ];

  const maxChart = Math.max(...data.registrations_chart.map(c => c.count), 1);

  return (
    <div className="max-w-[1100px]">
      <h1 className="text-[28px] font-black text-ink mb-1">Дашборд</h1>
      <p className="text-[13px] text-muted mb-8">Огляд платформи Carbit</p>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {cards.map(({ label, value, sub, accent }) => (
          <div key={label} className="bg-white border border-border rounded-xl p-5">
            <div className="text-[12px] text-muted mb-2">{label}</div>
            <div className="text-[28px] font-black text-ink leading-none">{value}</div>
            <div className={cn("text-[11px] mt-1.5", accent ? "text-emerald-dark font-semibold" : "text-muted")}>{sub}</div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
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
      </div>
    </div>
  );
}
