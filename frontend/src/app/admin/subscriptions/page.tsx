"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { adminApi } from "@/lib/admin-api";
import { cn } from "@/lib/utils";

export default function AdminSubscriptionsPage() {
  const [rows, setRows] = useState<{ plan: string; plan_name: string; count: number; revenue_uah: number }[]>([]);
  const [finance, setFinance] = useState<Awaited<ReturnType<typeof adminApi.finance>> | null>(null);

  useEffect(() => {
    Promise.all([adminApi.subscriptions(), adminApi.finance()])
      .then(([subs, fin]) => {
        setRows(subs);
        setFinance(fin);
      })
      .catch(() => {});
  }, []);

  const total = rows.reduce((s, r) => s + r.count, 0);
  const revenue = rows.reduce((s, r) => s + r.revenue_uah, 0);
  const liqpay = finance?.liqpay;

  return (
    <div className="max-w-[900px]">
      <h1 className="text-[28px] font-black text-ink mb-1">Підписки</h1>
      <p className="text-[13px] text-muted mb-8">
        {total} користувачів · {revenue.toLocaleString("uk-UA")} ₴/міс оцінка
        {liqpay ? ` · LiqPay MRR ${liqpay.recurring_mrr_uah.toLocaleString("uk-UA")} ₴` : ""}
      </p>

      {liqpay && (
        <div className="mb-6 grid gap-3 sm:grid-cols-4">
          {[
            ["Active", liqpay.active_recurring, false],
            ["Past due", liqpay.past_due, liqpay.past_due > 0],
            ["Експайр 7д", liqpay.expiring_7d, false],
            ["Прострочені", liqpay.expired_plans, liqpay.expired_plans > 0],
          ].map(([label, value, danger]) => (
            <div key={String(label)} className="rounded-xl border border-border bg-white p-4">
              <div className="text-[11px] text-muted">{label}</div>
              <div className={cn("mt-1 text-[22px] font-black", danger ? "text-red-600" : "text-ink")}>
                {value}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mb-6 overflow-x-auto rounded-xl border border-border bg-white">
        <table className="w-full min-w-[720px] text-[13px]">
          <thead>
            <tr className="border-b border-border bg-surface text-left text-[11px] uppercase tracking-wide text-muted">
              <th className="px-4 py-3 font-semibold">Тариф</th>
              <th className="px-4 py-3 font-semibold">Користувачів</th>
              <th className="px-4 py-3 font-semibold">Частка</th>
              <th className="px-4 py-3 font-semibold text-right">Дохід/міс</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.plan} className="border-b border-border last:border-0">
                <td className="px-4 py-4 font-semibold text-ink">{r.plan_name}</td>
                <td className="px-4 py-4">{r.count}</td>
                <td className="px-4 py-4 text-muted">{total ? Math.round((r.count / total) * 100) : 0}%</td>
                <td className="px-4 py-4 text-right font-semibold">{r.revenue_uah.toLocaleString("uk-UA")} ₴</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Link href="/admin/finance" className="text-[13px] font-semibold text-emerald-dark hover:underline">
        Детальна аналітика платежів →
      </Link>
    </div>
  );
}
