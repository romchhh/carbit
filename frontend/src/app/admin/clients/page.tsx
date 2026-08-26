"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { adminApi, AdminUser } from "@/lib/admin-api";
import { getAdminToken } from "@/lib/admin-storage";
import { formatKyivDate } from "@/lib/datetime";
import { PLAN_LABELS, cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { UserAvatar } from "@/components/ui/UserAvatar";

export default function AdminClientsPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [plan, setPlan] = useState("");
  const [loading, setLoading] = useState(true);
  const adminToken = getAdminToken();

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

      <div className="mb-6 flex flex-col gap-3 sm:flex-row">
        <input
          className="auth-input w-full flex-1 sm:max-w-[280px]"
          placeholder="Пошук email або ім'я..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
        />
        <select
          className="auth-input w-full sm:w-[140px]"
          value={plan}
          onChange={e => { setPlan(e.target.value); setPage(1); }}
        >
          <option value="">Всі тарифи</option>
          {Object.entries(PLAN_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border bg-white">
        <table className="w-full min-w-[720px] text-[13px]">
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
                  <div className="flex items-center gap-3">
                    <UserAvatar
                      name={u.name}
                      avatarUrl={u.avatar_url}
                      accessToken={adminToken}
                      className="h-9 w-9 shrink-0 text-[12px]"
                    />
                    <div>
                      <Link href={`/admin/clients/${u.id}`} className="font-semibold text-ink hover:text-emerald-dark">
                        {u.name}
                      </Link>
                      <div className="text-[11px] text-muted">{u.email}</div>
                    </div>
                  </div>
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
                  {formatKyivDate(u.created_at)}
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
