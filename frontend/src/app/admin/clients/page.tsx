"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { adminApi, AdminUser } from "@/lib/admin-api";
import { PLAN_LABELS, cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";

export default function AdminClientsPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [plan, setPlan] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.users(page, search, plan);
      setUsers(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, [page, search, plan]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="max-w-[1100px]">
      <h1 className="text-[28px] font-black text-ink mb-1">Клієнти</h1>
      <p className="text-[13px] text-muted mb-6">{total} користувачів</p>

      <div className="flex gap-3 mb-6">
        <input
          className="auth-input flex-1 max-w-[280px]"
          placeholder="Пошук email або ім'я..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
        />
        <select
          className="auth-input w-[140px]"
          value={plan}
          onChange={e => { setPlan(e.target.value); setPage(1); }}
        >
          <option value="">Всі тарифи</option>
          {Object.entries(PLAN_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>

      <div className="bg-white border border-border rounded-xl overflow-hidden">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-border bg-surface text-left text-[11px] uppercase tracking-wide text-muted">
              <th className="px-4 py-3 font-semibold">Клієнт</th>
              <th className="px-4 py-3 font-semibold">Тариф</th>
              <th className="px-4 py-3 font-semibold">Telegram</th>
              <th className="px-4 py-3 font-semibold">Пошуки</th>
              <th className="px-4 py-3 font-semibold">Статус</th>
              <th className="px-4 py-3 font-semibold">Дата</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-12 text-center text-muted">Завантаження...</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-12 text-center text-muted">Немає клієнтів</td></tr>
            ) : users.map(u => (
              <tr key={u.id} className="border-b border-border last:border-0 hover:bg-surface/50">
                <td className="px-4 py-3">
                  <Link href={`/admin/clients/${u.id}`} className="font-semibold text-ink hover:text-emerald-dark">
                    {u.name}
                  </Link>
                  <div className="text-[11px] text-muted">{u.email}</div>
                </td>
                <td className="px-4 py-3">
                  <Badge variant="outline">{PLAN_LABELS[u.plan] ?? u.plan}</Badge>
                  {u.is_trial_active && <span className="ml-1 text-[10px] text-emerald-dark">trial</span>}
                </td>
                <td className="px-4 py-3">{u.telegram_connected ? "✓" : "—"}</td>
                <td className="px-4 py-3">{u.searches_count}</td>
                <td className="px-4 py-3">
                  <span className={cn("text-[12px] font-medium", u.is_active ? "text-emerald-dark" : "text-red-500")}>
                    {u.is_active ? "Активний" : "Заблокований"}
                  </span>
                </td>
                <td className="px-4 py-3 text-muted">
                  {new Date(u.created_at).toLocaleDateString("uk-UA")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {total > 20 && (
        <div className="flex justify-center gap-2 mt-4">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="px-3 py-1.5 text-[12px] border border-border rounded-lg disabled:opacity-40">←</button>
          <span className="px-3 py-1.5 text-[12px] text-muted">{page} / {Math.ceil(total / 20)}</span>
          <button disabled={page >= Math.ceil(total / 20)} onClick={() => setPage(p => p + 1)} className="px-3 py-1.5 text-[12px] border border-border rounded-lg disabled:opacity-40">→</button>
        </div>
      )}
    </div>
  );
}
