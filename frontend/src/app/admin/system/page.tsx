"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { adminApi, type AdminSystem } from "@/lib/admin-api";
import { AdminStatusBadge } from "@/components/admin/AdminCharts";
import { formatKyivDateTime } from "@/lib/datetime";
import { cn } from "@/lib/utils";

function formatDuration(seconds: number | null) {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds} с тому`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} хв тому`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h} год ${m} хв тому`;
}

const STATUS_LABELS: Record<string, string> = {
  success: "Успішно",
  partial: "Частково",
  failed: "Помилка",
  running: "В процесі",
};

export default function AdminSystemPage() {
  const [data, setData] = useState<AdminSystem | null>(null);

  useEffect(() => {
    adminApi.system().then(setData).catch(() => {});
  }, []);

  if (!data) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
      </div>
    );
  }

  const infra = [
    { label: "База даних", ok: data.database_ok },
    { label: "KV-сховище", ok: data.kv_store_ok },
  ];

  const settings = data.parser_settings;

  return (
    <div className="max-w-[1100px]">
      <h1 className="text-[28px] font-black text-ink mb-1">Система</h1>
      <p className="text-[13px] text-muted mb-8">Інфраструктура, інтеграції та стан парсингу</p>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-border bg-white p-5">
          <div className="text-[12px] text-muted mb-2">Планувальник</div>
          <AdminStatusBadge status={data.scheduler_status} />
          <div className="mt-2 text-[11px] text-muted">
            Останній запуск: {formatDuration(data.seconds_since_last_run)}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-white p-5">
          <div className="text-[12px] text-muted mb-2">Активних job-ів</div>
          <div className="text-[24px] font-black text-ink">{data.running_parse_jobs}</div>
        </div>
        <div className="rounded-xl border border-border bg-white p-5">
          <div className="text-[12px] text-muted mb-2">Telegram-каналів</div>
          <div className="text-[24px] font-black text-ink">{data.telegram_channels}</div>
        </div>
        <div className="rounded-xl border border-border bg-white p-5">
          <div className="text-[12px] text-muted mb-2">Інтервал парсингу</div>
          <div className="text-[24px] font-black text-ink">{settings.interval_seconds} с</div>
          <div className="mt-1 text-[11px] text-muted">
            {settings.enabled ? "Автопарсинг увімкнено" : "Автопарсинг вимкнено"}
          </div>
        </div>
      </div>

      <div className="mb-8 grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-border bg-white p-6">
          <h2 className="text-[16px] font-bold text-ink mb-4">Інфраструктура</h2>
          <div className="space-y-3">
            {infra.map(({ label, ok }) => (
              <div key={label} className="flex items-center justify-between rounded-xl bg-surface/50 px-4 py-3">
                <span className="text-[13px] font-medium text-ink">{label}</span>
                <span className={cn(
                  "rounded-full px-2.5 py-1 text-[11px] font-bold",
                  ok ? "bg-emerald/15 text-emerald-dark" : "bg-red-100 text-red-600",
                )}>
                  {ok ? "OK" : "Помилка"}
                </span>
              </div>
            ))}
            <div className="flex items-center justify-between rounded-xl bg-surface/50 px-4 py-3">
              <span className="text-[13px] font-medium text-ink">Режим DEBUG</span>
              <span className={cn(
                "rounded-full px-2.5 py-1 text-[11px] font-bold",
                data.debug_mode ? "bg-amber-100 text-amber-700" : "bg-emerald/15 text-emerald-dark",
              )}>
                {data.debug_mode ? "Увімкнено" : "Вимкнено"}
              </span>
            </div>
            <div className="rounded-xl bg-surface/50 px-4 py-3 text-[12px] text-muted">
              Frontend: <span className="font-medium text-ink">{data.frontend_url}</span>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-white p-6">
          <h2 className="text-[16px] font-bold text-ink mb-4">Інтеграції</h2>
          <div className="space-y-3">
            {data.integrations.map(item => (
              <div key={item.key} className="flex items-start justify-between gap-3 rounded-xl bg-surface/50 px-4 py-3">
                <div>
                  <div className="text-[13px] font-medium text-ink">{item.name}</div>
                  <div className="mt-0.5 text-[11px] text-muted">{item.detail}</div>
                </div>
                <span className={cn(
                  "shrink-0 rounded-full px-2.5 py-1 text-[11px] font-bold",
                  item.ok ? "bg-emerald/15 text-emerald-dark" : "bg-red-100 text-red-600",
                )}>
                  {item.ok ? "OK" : "Ні"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mb-8 rounded-2xl border border-border bg-white p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h2 className="text-[16px] font-bold text-ink">Налаштування парсера</h2>
          <Link href="/admin/parsing" className="text-[12px] font-semibold text-emerald hover:underline">
            Редагувати →
          </Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 text-[13px]">
          {[
            ["Автопарсинг", settings.enabled ? "Увімкнено" : "Вимкнено"],
            ["Telegram-джерело", settings.telegram_enabled ? "Увімкнено" : "Вимкнено"],
            ["Telegram-сповіщення", settings.notify_telegram ? "Увімкнено" : "Вимкнено"],
            ["Кеш TTL", `${settings.cache_ttl_seconds} с`],
            ["Макс. на групу", String(settings.max_listings_per_group)],
            ["Історія Telegram", `${settings.telegram_history_limit} повідомлень`],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg border border-border/70 px-3 py-2.5">
              <div className="text-[11px] text-muted">{label}</div>
              <div className="font-semibold text-ink">{value}</div>
            </div>
          ))}
        </div>
      </div>

      {data.last_run && (
        <div className="rounded-2xl border border-border bg-white p-6">
          <h2 className="text-[16px] font-bold text-ink mb-4">Останній запуск парсингу</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 text-[13px]">
            <div>
              <div className="text-[11px] text-muted">Час</div>
              <div className="font-semibold">{formatKyivDateTime(data.last_run.started_at)}</div>
            </div>
            <div>
              <div className="text-[11px] text-muted">Статус</div>
              <div className="font-semibold">{STATUS_LABELS[data.last_run.status] ?? data.last_run.status}</div>
            </div>
            <div>
              <div className="text-[11px] text-muted">Знайдено / нових</div>
              <div className="font-semibold">{data.last_run.listings_found} / {data.last_run.listings_new}</div>
            </div>
            <div>
              <div className="text-[11px] text-muted">Telegram</div>
              <div className="font-semibold">{data.last_run.notifications_sent} відправлено</div>
            </div>
          </div>
          {data.last_run.error && (
            <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-[12px] text-red-600">{data.last_run.error}</p>
          )}
        </div>
      )}
    </div>
  );
}
