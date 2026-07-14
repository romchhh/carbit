"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { adminApi, type AdminBillingSubscription } from "@/lib/admin-api";
import { formatKyivDate } from "@/lib/datetime";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";

const STATUS_LABELS: Record<string, string> = {
  pending: "Очікує",
  active: "Активні",
  past_due: "Past due",
  failed: "Невдалі",
  cancelled: "Скасовані",
};

export default function AdminFinancePage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof adminApi.finance>> | null>(null);

  useEffect(() => {
    adminApi.finance().then(setData);
  }, []);

  if (!data) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-2 border-emerald border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const liqpay = data.liqpay;
  const issues = data.issues ?? [];
  const statusEntries = Object.entries(liqpay?.by_status ?? {}).filter(([, n]) => n > 0);
  const statusTotal = statusEntries.reduce((s, [, n]) => s + n, 0) || 1;

  return (
    <div className="max-w-[960px]">
      <h1 className="text-[28px] font-black text-ink mb-1">Фінанси</h1>
      <p className="text-[13px] text-muted mb-8">
        Оцінка за тарифами + реальний стан рекурентних підписок LiqPay
      </p>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          ["MRR (тарифи)", `${data.mrr_uah.toLocaleString("uk-UA")} ₴`],
          ["ARR", `${data.arr_uah.toLocaleString("uk-UA")} ₴`],
          ["Платних користувачів", String(data.paid_count)],
          ["ARPU", `${data.avg_revenue_per_user} ₴`],
        ].map(([label, value]) => (
          <div key={label} className="bg-white border border-border rounded-xl p-5">
            <div className="text-[12px] text-muted mb-2">{label}</div>
            <div className="text-[24px] font-black text-ink">{value}</div>
          </div>
        ))}
      </div>

      {liqpay && (
        <>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {[
              {
                label: "LiqPay MRR",
                value: `${liqpay.recurring_mrr_uah.toLocaleString("uk-UA")} ₴`,
                sub: `${liqpay.active_recurring} автоплатежів`,
                accent: true,
              },
              {
                label: "Past due",
                value: String(liqpay.past_due),
                sub: `${liqpay.failed_charges_total} failed charges`,
                accent: liqpay.past_due > 0,
                danger: liqpay.past_due > 0,
              },
              {
                label: "Закінчуються (7д)",
                value: String(liqpay.expiring_7d),
                sub: "plan_expires_at",
              },
              {
                label: "Прострочені плани",
                value: String(liqpay.expired_plans),
                sub: "потрібен даунгрейд",
                danger: liqpay.expired_plans > 0,
              },
            ].map(card => (
              <div key={card.label} className="bg-white border border-border rounded-xl p-5">
                <div className="text-[12px] text-muted mb-2">{card.label}</div>
                <div
                  className={cn(
                    "text-[24px] font-black leading-none",
                    card.danger ? "text-red-600" : "text-ink",
                  )}
                >
                  {card.value}
                </div>
                {card.sub && (
                  <div
                    className={cn(
                      "mt-1.5 text-[11px]",
                      card.accent && !card.danger ? "font-semibold text-emerald-dark" : "text-muted",
                      card.danger && "font-semibold text-red-600",
                    )}
                  >
                    {card.sub}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="mb-8 grid gap-6 lg:grid-cols-2">
            <div className="bg-white border border-border rounded-xl p-6">
              <h2 className="text-[15px] font-bold text-ink mb-4">Статуси LiqPay</h2>
              <div className="space-y-3">
                {statusEntries.length === 0 ? (
                  <p className="text-[13px] text-muted">Записів підписок ще немає</p>
                ) : (
                  statusEntries.map(([status, count]) => (
                    <div key={status} className="flex items-center gap-3">
                      <span className="w-28 shrink-0 text-[13px] text-ink">
                        {STATUS_LABELS[status] ?? status}
                      </span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface">
                        <div
                          className={cn(
                            "h-full rounded-full",
                            status === "past_due" || status === "failed"
                              ? "bg-red-500"
                              : status === "active"
                                ? "bg-emerald"
                                : "bg-ink/40",
                          )}
                          style={{ width: `${(count / statusTotal) * 100}%` }}
                        />
                      </div>
                      <span className="w-8 text-right text-[13px] font-semibold text-ink">{count}</span>
                    </div>
                  ))
                )}
              </div>
              <p className="mt-4 text-[11px] text-muted">
                Trial: {data.trial_count} · Pending checkout: {liqpay.pending} · Скасовані:{" "}
                {liqpay.cancelled}
              </p>
            </div>

            <div className="bg-white border border-border rounded-xl p-6">
              <h2 className="text-[15px] font-bold text-ink mb-4">Дохід по тарифах (оцінка)</h2>
              <div className="space-y-3">
                {data.by_plan.filter(p => p.revenue_uah > 0).map(p => (
                  <div
                    key={p.plan}
                    className="flex items-center justify-between border-b border-border py-2 last:border-0"
                  >
                    <span className="text-[13px] font-medium text-ink">{p.plan_name}</span>
                    <span className="text-[13px] text-muted">{p.count} × </span>
                    <span className="text-[13px] font-bold text-ink">
                      {p.revenue_uah.toLocaleString("uk-UA")} ₴
                    </span>
                  </div>
                ))}
                {data.by_plan.every(p => p.revenue_uah === 0) && (
                  <p className="text-[13px] text-muted">Платних підписок поки немає</p>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      <div className="mb-6 bg-white border border-border rounded-xl p-6">
        <h2 className="mb-1 text-[15px] font-bold text-ink">Проблемні платежі</h2>
        <p className="mb-4 text-[12px] text-muted">Past due та failed — потребують уваги</p>
        {issues.length === 0 ? (
          <p className="text-[13px] text-muted">Немає проблемних підписок 👍</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-border bg-surface text-left text-[11px] uppercase tracking-wide text-muted">
                  <th className="px-3 py-2.5 font-semibold">Клієнт</th>
                  <th className="px-3 py-2.5 font-semibold">Тариф</th>
                  <th className="px-3 py-2.5 font-semibold">Статус</th>
                  <th className="px-3 py-2.5 font-semibold">Failed</th>
                  <th className="px-3 py-2.5 font-semibold text-right">Сума</th>
                </tr>
              </thead>
              <tbody>
                {issues.map((row: AdminBillingSubscription) => (
                  <tr key={row.id} className="border-b border-border last:border-0 hover:bg-surface/50">
                    <td className="px-3 py-3">
                      {row.user_id ? (
                        <Link
                          href={`/admin/clients/${row.user_id}`}
                          className="font-semibold text-emerald-dark hover:underline"
                        >
                          {row.user_name || row.user_email}
                        </Link>
                      ) : (
                        "—"
                      )}
                      <div className="text-[11px] text-muted">{row.user_email}</div>
                    </td>
                    <td className="px-3 py-3">{row.plan_name}</td>
                    <td className="px-3 py-3">
                      <Badge variant={row.status === "past_due" || row.status === "failed" ? "red" : "outline"}>
                        {STATUS_LABELS[row.status] ?? row.status}
                      </Badge>
                      <div className="mt-1 text-[10px] text-muted">{formatKyivDate(row.updated_at)}</div>
                    </td>
                    <td className="px-3 py-3 font-semibold text-red-600">{row.failed_charges}</td>
                    <td className="px-3 py-3 text-right font-semibold">
                      {row.amount.toLocaleString("uk-UA")} {row.currency}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-border bg-surface/50 p-4 text-[12px] text-muted">
        <strong className="text-ink">Як читати:</strong> «MRR (тарифи)» — оцінка з призначених планів.
        «LiqPay MRR» — сума активних рекурентних підписок. Past due / failed беруться з callback LiqPay.
      </div>
    </div>
  );
}
