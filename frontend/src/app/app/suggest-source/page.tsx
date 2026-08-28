"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AppEmpty, AppPage, AppSection } from "@/components/layout/AppPage";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { IconGlobe } from "@/components/icons";
import { ApiError, sourceRequests as sourceRequestsApi } from "@/lib/api";
import type { MonitoringSourceRequest } from "@/types/api";
import { formatKyivDateTime } from "@/lib/datetime";
import { cn } from "@/lib/utils";

const STATUS_LABELS: Record<MonitoringSourceRequest["status"], string> = {
  pending: "Очікує",
  in_review: "На розгляді",
  approved: "Схвалено",
  rejected: "Відхилено",
};

const STATUS_VARIANT: Record<MonitoringSourceRequest["status"], "gray" | "outline" | "emerald" | "red"> = {
  pending: "gray",
  in_review: "outline",
  approved: "emerald",
  rejected: "red",
};

export default function SuggestSourcePage() {
  const [items, setItems] = useState<MonitoringSourceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [url, setUrl] = useState("");
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await sourceRequestsApi.list());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    const trimmedUrl = url.trim();
    if (!trimmedUrl) {
      setError("Вкажіть посилання на канал або сайт");
      return;
    }
    setSubmitting(true);
    try {
      await sourceRequestsApi.create({
        url: trimmedUrl,
        comment: comment.trim() || undefined,
      });
      setUrl("");
      setComment("");
      setSuccess("Заявку надіслано. Ми розглянемо її та повідомимо, коли джерело буде підключено.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося надіслати заявку");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AppPage
      narrow
      title="Запропонувати джерело"
      description="Telegram-канал, сайт оголошень або інший ресурс — додамо до моніторингу після перевірки."
    >
      <div className="space-y-4 sm:space-y-5">
        <AppSection className="!border-border/60 !bg-white">
          <div className="flex items-start gap-3 rounded-xl bg-emerald/5 px-4 py-3.5 text-[13px] leading-relaxed text-muted">
            <IconGlobe size={20} className="mt-0.5 shrink-0 text-emerald-dark" />
            <p>
              Зараз Carbit моніторить{" "}
              <strong className="text-ink">AUTO.RIA</strong>, <strong className="text-ink">OLX</strong> та{" "}
              <strong className="text-ink">Telegram-канали</strong>. Надішліть посилання на корисний канал або
              майданчик — питання по заявках у{" "}
              <Link href="/app/account" className="font-semibold text-emerald-dark hover:underline">
                акаунті
              </Link>
              .
            </p>
          </div>

          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <div>
              <label htmlFor="source-url" className="mb-1.5 block text-[13px] font-semibold text-ink">
                Посилання *
              </label>
              <input
                id="source-url"
                type="text"
                className="auth-input w-full"
                placeholder="https://t.me/channel, olx.ua/..., auto.ria.com/..."
                value={url}
                onChange={e => setUrl(e.target.value)}
                disabled={submitting}
                maxLength={2048}
              />
              <p className="mt-1.5 text-[12px] text-muted">
                Можна вставити @username Telegram, t.me/… або повне посилання на сайт.
              </p>
            </div>

            <div>
              <label htmlFor="source-comment" className="mb-1.5 block text-[13px] font-semibold text-ink">
                Коментар <span className="font-normal text-muted">(необовʼязково)</span>
              </label>
              <textarea
                id="source-comment"
                className="auth-input w-full min-h-[96px] resize-y"
                placeholder="Чому це джерело корисне? Регіон, тип авто, особливості..."
                value={comment}
                onChange={e => setComment(e.target.value)}
                disabled={submitting}
                maxLength={2000}
              />
            </div>

            {error && (
              <p className="rounded-xl bg-red-50 px-4 py-3 text-[13px] text-red-600">{error}</p>
            )}
            {success && (
              <p className="rounded-xl bg-emerald/10 px-4 py-3 text-[13px] text-emerald-dark">{success}</p>
            )}

            <Button type="submit" variant="emerald" size="md" disabled={submitting} className="w-full sm:w-auto">
              {submitting ? "Надсилання..." : "Надіслати заявку"}
            </Button>
          </form>
        </AppSection>

        <AppSection className="!border-border/60 !bg-white">
          <h2 className="text-[17px] font-bold text-ink">Ваші заявки</h2>
          <p className="mt-1 text-[13px] text-muted">Історія пропозицій і їхній статус.</p>

          {loading ? (
            <p className="mt-6 text-center text-[13px] text-muted">Завантаження...</p>
          ) : items.length === 0 ? (
            <AppEmpty className="mt-5 border-border/50 bg-surface/30 py-10">
              Ще немає заявок — надішліть першу пропозицію вище.
            </AppEmpty>
          ) : (
            <ul className="mt-5 divide-y divide-border/60 overflow-hidden rounded-xl border border-border/60">
              {items.map(item => (
                <li key={item.id} className="bg-white px-4 py-3.5 sm:px-5">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="break-all text-[13px] font-semibold text-emerald-dark hover:underline"
                    >
                      {item.url}
                    </a>
                    <Badge variant={STATUS_VARIANT[item.status]}>{STATUS_LABELS[item.status]}</Badge>
                  </div>
                  {item.comment && (
                    <p className="mt-2 text-[12px] leading-relaxed text-muted">{item.comment}</p>
                  )}
                  <p className={cn("mt-2 text-[11px] text-muted/80")}>
                    {formatKyivDateTime(item.created_at)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </AppSection>
      </div>
    </AppPage>
  );
}
