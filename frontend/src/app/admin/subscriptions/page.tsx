"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";

export default function AdminSubscriptionsPage() {
  const [rows, setRows] = useState<{ plan: string; plan_name: string; count: number; revenue_uah: number }[]>([]);

  useEffect(() => {
    adminApi.subscriptions().then(setRows);
  }, []);

  const total = rows.reduce((s, r) => s + r.count, 0);
  const revenue = rows.reduce((s, r) => s + r.revenue_uah, 0);

  return (
    <div className="max-w-[800px]">
      <h1 className="text-[28px] font-black text-ink mb-1">Підписки</h1>
      <p className="text-[13px] text-muted mb-8">{total} користувачів · {revenue.toLocaleString("uk-UA")} ₴/міс</p>

      <div className="bg-white border border-border rounded-xl overflow-hidden">
        <table className="w-full text-[13px]">
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
    </div>
  );
}
