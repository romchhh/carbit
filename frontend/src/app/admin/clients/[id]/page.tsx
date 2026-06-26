"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { adminApi, AdminUserDetail } from "@/lib/admin-api";
import { PLAN_LABELS } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export default function AdminClientDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [user, setUser] = useState<AdminUserDetail | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    params.then(p => adminApi.user(p.id).then(setUser));
  }, [params]);

  if (!user) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-2 border-emerald border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const changePlan = async (plan: string) => {
    setSaving(true);
    try {
      await adminApi.updateUser(user.id, { plan });
      setUser(await adminApi.user(user.id));
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async () => {
    setSaving(true);
    try {
      await adminApi.updateUser(user.id, { is_active: !user.is_active });
      setUser(await adminApi.user(user.id));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-[800px]">
      <Link href="/admin/clients" className="text-[13px] text-muted hover:text-ink mb-4 inline-block">← Клієнти</Link>
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-[28px] font-black text-ink">{user.name}</h1>
          <p className="text-[13px] text-muted">{user.email}</p>
        </div>
        <Badge variant={user.is_active ? "emerald" : "red"}>
          {user.is_active ? "Активний" : "Заблокований"}
        </Badge>
      </div>

      <div className="grid sm:grid-cols-3 gap-4 mb-6">
        {[
          ["Пошуків", user.searches_count],
          ["Сповіщень", user.notifications_count],
          ["Обраних", user.favorites_count],
        ].map(([l, v]) => (
          <div key={l} className="bg-white border border-border rounded-xl p-4 text-center">
            <div className="text-[24px] font-black text-ink">{v}</div>
            <div className="text-[11px] text-muted mt-1">{l}</div>
          </div>
        ))}
      </div>

      <section className="bg-white border border-border rounded-xl p-6 mb-4 space-y-4">
        <h2 className="text-[15px] font-bold text-ink">Тариф</h2>
        <div className="flex flex-wrap gap-2">
          {Object.entries(PLAN_LABELS).map(([k, v]) => (
            <button
              key={k}
              disabled={saving}
              onClick={() => changePlan(k)}
              className={`px-3 py-1.5 rounded-lg text-[12px] font-medium border transition-colors ${
                user.plan === k ? "bg-ink text-white border-ink" : "border-border text-muted hover:border-ink/30"
              }`}
            >
              {v}
            </button>
          ))}
        </div>
        {user.is_trial_active && (
          <p className="text-[12px] text-emerald-dark">Trial до {user.trial_ends_at ? new Date(user.trial_ends_at).toLocaleDateString("uk-UA") : "—"}</p>
        )}
      </section>

      <section className="bg-white border border-border rounded-xl p-6 mb-4">
        <h2 className="text-[15px] font-bold text-ink mb-3">Telegram</h2>
        <p className="text-[13px] text-muted">
          {user.telegram_connected
            ? `Підключено ${user.telegram_username ? `@${user.telegram_username}` : ""}`
            : "Не підключено"}
        </p>
      </section>

      {user.searches.length > 0 && (
        <section className="bg-white border border-border rounded-xl p-6 mb-4">
          <h2 className="text-[15px] font-bold text-ink mb-3">Пошукові запити</h2>
          <div className="space-y-2">
            {user.searches.map(s => (
              <div key={s.id} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                <span className="text-[13px] font-medium text-ink">{s.name}</span>
                <span className="text-[12px] text-muted">
                  {s.is_active ? "активний" : "пауза"} · {s.new_count} нових · {s.total_count} всього
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      <Button variant="danger" size="sm" loading={saving} onClick={toggleActive}>
        {user.is_active ? "Заблокувати акаунт" : "Розблокувати акаунт"}
      </Button>
    </div>
  );
}
