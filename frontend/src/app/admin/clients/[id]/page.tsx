"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { adminApi, AdminUserDetail, type AdminBillingSubscription } from "@/lib/admin-api";
import { getAdminToken } from "@/lib/admin-storage";
import { formatKyivDate } from "@/lib/datetime";
import { PLAN_LABELS, cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { UserAvatar } from "@/components/ui/UserAvatar";

const STATUS_LABELS: Record<string, string> = {
  pending: "Очікує",
  active: "Активна",
  past_due: "Прострочена оплата",
  failed: "Невдала",
  cancelled: "Скасована",
};

function statusVariant(status: string): "emerald" | "red" | "outline" {
  if (status === "active") return "emerald";
  if (status === "past_due" || status === "failed") return "red";
  return "outline";
}

function BillingRow({ sub }: { sub: AdminBillingSubscription }) {
  return (
    <div className="rounded-xl border border-border/80 bg-surface/40 px-4 py-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[13px] font-semibold text-ink">{sub.plan_name}</span>
            <Badge variant={statusVariant(sub.status)}>
              {STATUS_LABELS[sub.status] ?? sub.status}
            </Badge>
            {sub.failed_charges > 0 && (
              <Badge variant="red">{sub.failed_charges} невдалих</Badge>
            )}
          </div>
          <p className="mt-1 font-mono text-[11px] text-muted break-all">{sub.order_id}</p>
        </div>
        <div className="text-right">
          <div className="text-[15px] font-black text-ink">
            {sub.amount.toLocaleString("uk-UA")} {sub.currency}
          </div>
          <div className="text-[11px] text-muted">/{sub.periodicity === "year" ? "рік" : "міс"}</div>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted">
        <span>Створено: {formatKyivDate(sub.created_at)}</span>
        {sub.last_status && <span>LiqPay: {sub.last_status}</span>}
        {sub.liqpay_payment_id && <span>payment_id: {sub.liqpay_payment_id}</span>}
        {sub.cancelled_at && <span>Скасовано: {formatKyivDate(sub.cancelled_at)}</span>}
      </div>
    </div>
  );
}

export default function AdminClientDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const [user, setUser] = useState<AdminUserDetail | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

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

  const deleteUser = async () => {
    setDeleting(true);
    setDeleteError("");
    try {
      await adminApi.deleteUser(user.id);
      router.push("/admin/clients");
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Не вдалося видалити користувача");
      setDeleting(false);
    }
  };

  const summary = user.billing_summary;
  const billing = user.billing_subscriptions ?? [];
  const searchesCount = user.searches?.length ?? user.searches_count ?? 0;

  return (
    <div className="max-w-[860px]">
      <Link href="/admin/clients" className="text-[13px] text-muted hover:text-ink mb-4 inline-block">← Клієнти</Link>
      <div className="flex items-start justify-between mb-8">
        <div className="flex items-center gap-4">
          <UserAvatar
            name={user.name}
            avatarUrl={user.avatar_url}
            accessToken={getAdminToken()}
            className="h-14 w-14 shrink-0 text-[18px]"
          />
          <div>
            <h1 className="text-[28px] font-black text-ink">{user.name}</h1>
            <p className="text-[13px] text-muted">{user.email}</p>
            <p className="mt-1 text-[11px] text-muted">
              З {formatKyivDate(user.created_at)} · ID {user.id.slice(0, 8)}…
            </p>
          </div>
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
        <div className="flex flex-wrap gap-3 text-[12px]">
          {user.is_trial_active && (
            <span className="text-emerald-dark">Trial до {formatKyivDate(user.trial_ends_at)}</span>
          )}
          {user.plan_expires_at && (
            <span className={cn(summary?.plan_expired ? "font-semibold text-red-600" : "text-muted")}>
              План діє до {formatKyivDate(user.plan_expires_at)}
              {summary?.plan_expired ? " · прострочено" : ""}
            </span>
          )}
          {!user.plan_expires_at && user.plan === "free" && (
            <span className="text-muted">Без дати закінчення (Free)</span>
          )}
        </div>
      </section>

      <section className="bg-white border border-border rounded-xl p-6 mb-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-[15px] font-bold text-ink">Платежі / LiqPay</h2>
          <div className="flex flex-wrap gap-1.5">
            {summary?.active_recurring && <Badge variant="emerald">Автоплатіж</Badge>}
            {summary?.past_due && <Badge variant="red">Past due</Badge>}
            {summary?.plan_expired && <Badge variant="red">План прострочено</Badge>}
            {(summary?.failed_charges ?? 0) > 0 && (
              <Badge variant="red">{summary?.failed_charges} failed</Badge>
            )}
          </div>
        </div>

        {billing.length === 0 ? (
          <p className="text-[13px] text-muted">Немає записів LiqPay для цього користувача.</p>
        ) : (
          <div className="space-y-3">
            {billing.map(sub => (
              <BillingRow key={sub.id} sub={sub} />
            ))}
          </div>
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
          <h2 className="text-[15px] font-bold text-ink mb-3">Моніторинги</h2>
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

      <div className="flex flex-wrap gap-2">
        <Button variant="danger" size="sm" loading={saving} onClick={toggleActive}>
          {user.is_active ? "Заблокувати акаунт" : "Розблокувати акаунт"}
        </Button>
        <Button
          variant="danger"
          size="sm"
          className="border-red-300 bg-red-50 text-red-700 hover:bg-red-100"
          onClick={() => {
            setDeleteError("");
            setDeleteOpen(true);
          }}
        >
          Видалити користувача
        </Button>
      </div>

      {deleteError && (
        <p className="mt-3 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-[12px] text-red-600">
          {deleteError}
        </p>
      )}

      <ConfirmDialog
        open={deleteOpen}
        title={`Видалити ${user.name}?`}
        description={`Буде остаточно видалено акаунт ${user.email}, усі моніторинги (${searchesCount}), обране, сповіщення та записи оплат. Активні підписки LiqPay буде скасовано. Цю дію не можна скасувати.`}
        confirmLabel="Видалити назавжди"
        cancelLabel="Скасувати"
        variant="danger"
        loading={deleting}
        onClose={() => {
          if (!deleting) setDeleteOpen(false);
        }}
        onConfirm={() => void deleteUser()}
      />
    </div>
  );
}
