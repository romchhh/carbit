"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";

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

  return (
    <div className="max-w-[900px]">
      <h1 className="text-[28px] font-black text-ink mb-1">Фінанси</h1>
      <p className="text-[13px] text-muted mb-8">Оцінка доходу на основі активних тарифів</p>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          ["MRR", `${data.mrr_uah.toLocaleString("uk-UA")} ₴`],
          ["ARR", `${data.arr_uah.toLocaleString("uk-UA")} ₴`],
          ["Платних", String(data.paid_count)],
          ["ARPU", `${data.avg_revenue_per_user} ₴`],
        ].map(([label, value]) => (
          <div key={label} className="bg-white border border-border rounded-xl p-5">
            <div className="text-[12px] text-muted mb-2">{label}</div>
            <div className="text-[24px] font-black text-ink">{value}</div>
          </div>
        ))}
      </div>

      <div className="bg-white border border-border rounded-xl p-6 mb-6">
        <h2 className="text-[15px] font-bold text-ink mb-4">Дохід по тарифах</h2>
        <div className="space-y-3">
          {data.by_plan.filter(p => p.revenue_uah > 0).map(p => (
            <div key={p.plan} className="flex items-center justify-between py-2 border-b border-border last:border-0">
              <span className="text-[13px] font-medium text-ink">{p.plan_name}</span>
              <span className="text-[13px] text-muted">{p.count} × </span>
              <span className="text-[13px] font-bold text-ink">{p.revenue_uah.toLocaleString("uk-UA")} ₴</span>
            </div>
          ))}
          {data.by_plan.every(p => p.revenue_uah === 0) && (
            <p className="text-[13px] text-muted">Платних підписок поки немає</p>
          )}
        </div>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-[13px] text-amber-800">
        <strong>Примітка:</strong> Дані розраховані на основі призначених тарифів. Реальні платежі через LiqPay/Mono Pay будуть підключені пізніше.
      </div>
    </div>
  );
}
