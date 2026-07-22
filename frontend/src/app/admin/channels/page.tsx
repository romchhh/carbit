"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ListingDetailModal } from "@/components/listings/ListingDetailModal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { TelethonSessionPanel } from "@/components/admin/TelethonSessionPanel";
import { adminApi, AdminApiError, type AdminTelegramChannel, type AdminTelegramWorkerStatus } from "@/lib/admin-api";
import { formatKyivDateTime } from "@/lib/datetime";
import { cn } from "@/lib/utils";
import type { Listing } from "@/types/api";

function formatPrice(price: number | null | undefined) {
  if (price == null) return "—";
  return `${Number(price).toLocaleString("uk-UA")} грн`;
}

export default function AdminTelegramChannelsPage() {
  const [channels, setChannels] = useState<AdminTelegramChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [title, setTitle] = useState("");
  const [adding, setAdding] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [channelListings, setChannelListings] = useState<Array<Record<string, unknown>>>([]);
  const [listingsLoading, setListingsLoading] = useState(false);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const [detailLoadingId, setDetailLoadingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<AdminTelegramChannel | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [workerStatus, setWorkerStatus] = useState<AdminTelegramWorkerStatus | null>(null);
  const [workerPoll, setWorkerPoll] = useState(3);
  const [workerSync, setWorkerSync] = useState(45);
  const [workerSaving, setWorkerSaving] = useState(false);
  const [telegramRunLoading, setTelegramRunLoading] = useState(false);

  const selected = channels.find(c => c.id === selectedId) ?? null;

  const loadWorkerStatus = useCallback(async () => {
    try {
      const data = await adminApi.telegramWorkerStatus();
      setWorkerStatus(data);
      setWorkerPoll(data.telegram_worker_poll_seconds);
      setWorkerSync(data.telegram_channel_sync_seconds);
    } catch {
      setWorkerStatus(null);
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [data] = await Promise.all([adminApi.telegramChannels(), loadWorkerStatus()]);
      setChannels(data);
    } finally {
      setLoading(false);
    }
  }, [loadWorkerStatus]);

  useEffect(() => {
    void load();
  }, [load]);

  const loadListings = useCallback(async (channelId: string) => {
    setListingsLoading(true);
    try {
      const data = await adminApi.telegramChannelListings(channelId, 60);
      setChannelListings(data);
    } finally {
      setListingsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setChannelListings([]);
      return;
    }
    void loadListings(selectedId);
  }, [selectedId, loadListings]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) return;
    setAdding(true);
    setMessage(null);
    try {
      const created = await adminApi.createTelegramChannel({
        username: username.trim(),
        title: title.trim() || undefined,
      });
      setUsername("");
      setTitle("");
      setMessage(`Додано ${created.username}`);
      await load();
      setSelectedId(created.id);
    } catch (err) {
      setMessage(err instanceof AdminApiError ? err.message : "Не вдалося додати канал");
    } finally {
      setAdding(false);
    }
  };

  const toggleEnabled = async (channel: AdminTelegramChannel) => {
    setMessage(null);
    try {
      await adminApi.updateTelegramChannel(channel.id, { enabled: !channel.enabled });
      await load();
    } catch (err) {
      setMessage(err instanceof AdminApiError ? err.message : "Помилка оновлення");
    }
  };

  const removeChannel = async (channel: AdminTelegramChannel) => {
    setDeleting(true);
    setMessage(null);
    try {
      await adminApi.deleteTelegramChannel(channel.id);
      if (selectedId === channel.id) setSelectedId(null);
      setMessage(`Видалено ${channel.username}`);
      setPendingDelete(null);
      await load();
    } catch (err) {
      setMessage(err instanceof AdminApiError ? err.message : "Помилка видалення");
    } finally {
      setDeleting(false);
    }
  };

  const openListing = async (id: string) => {
    setDetailLoadingId(id);
    try {
      const listing = await adminApi.listing(id);
      setSelectedListing(listing);
    } finally {
      setDetailLoadingId(null);
    }
  };

  const saveWorkerDelays = async () => {
    setWorkerSaving(true);
    setMessage(null);
    try {
      await adminApi.updateParserSettings({
        telegram_worker_poll_seconds: workerPoll,
        telegram_channel_sync_seconds: workerSync,
      });
      setMessage("Затримки worker збережено (підхопить без перезапуску)");
      await loadWorkerStatus();
    } catch (err) {
      setMessage(err instanceof AdminApiError ? err.message : "Не вдалося зберегти");
    } finally {
      setWorkerSaving(false);
    }
  };

  const runTelegramCollect = async () => {
    setTelegramRunLoading(true);
    setMessage(null);
    try {
      await adminApi.triggerParserRunSource("telegram");
      setMessage("Плановий збір Telegram запущено (фільтри користувачів)");
      await loadWorkerStatus();
    } catch (err) {
      setMessage(err instanceof AdminApiError ? err.message : "Помилка запуску");
    } finally {
      setTelegramRunLoading(false);
    }
  };

  if (loading && channels.length === 0) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="max-w-[1200px]">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-black text-ink">Telegram-канали</h1>
          <p className="mt-1 text-[13px] text-muted">
            Джерела для парсингу · клік по каналу показує зібрані авто
          </p>
        </div>
        <Link href="/admin/parsing" className="text-[12px] font-semibold text-emerald hover:underline">
          ← Парсинг
        </Link>
      </div>

      {message && (
        <div className="mb-5 rounded-xl border border-emerald/20 bg-emerald-light/40 px-4 py-3 text-[13px] text-emerald-dark">
          {message}
        </div>
      )}

      <TelethonSessionPanel
        onMessage={setMessage}
        workerOnline={Boolean(workerStatus?.worker_online)}
      />

      <section className="mb-6 rounded-2xl border border-border/70 bg-white p-4 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-[16px] font-bold text-ink">Telegram worker</h2>
            <p className="mt-1 text-[12px] text-muted">
              Окремий процес: realtime-пости + черга keyword/фото. Плановий цикл по фільтрах — кнопка нижче або scheduler.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void runTelegramCollect()}
            disabled={telegramRunLoading || workerStatus?.telegram_enabled === false}
            className="rounded-full bg-sky-600 px-4 py-2 text-[12px] font-semibold text-white hover:bg-sky-700 disabled:opacity-60"
          >
            {telegramRunLoading ? "Запуск…" : "Запустити збір зараз"}
          </button>
        </div>

        {workerStatus && (
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-border/60 bg-surface/40 px-3 py-2.5">
              <div className="text-[10px] font-bold uppercase tracking-wide text-muted">Worker</div>
              <div
                className={cn(
                  "mt-1 text-[14px] font-bold",
                  workerStatus.worker_online ? "text-emerald-dark" : "text-amber-700",
                )}
              >
                {workerStatus.worker_online
                  ? "Online"
                  : workerStatus.worker_heartbeat_age_seconds != null
                    ? `Offline (${Math.round(workerStatus.worker_heartbeat_age_seconds)} с тому)`
                    : "Немає heartbeat"}
              </div>
            </div>
            <div className="rounded-xl border border-border/60 bg-surface/40 px-3 py-2.5">
              <div className="text-[10px] font-bold uppercase tracking-wide text-muted">Черга keyword</div>
              <div className="mt-1 text-[13px] text-ink">
                {workerStatus.keyword_queue.pending} очікує · {workerStatus.keyword_queue.running} в роботі
              </div>
            </div>
            <div className="rounded-xl border border-border/60 bg-surface/40 px-3 py-2.5 sm:col-span-2">
              <div className="text-[10px] font-bold uppercase tracking-wide text-muted">Розклад</div>
              <div className="mt-1 text-[12px] text-muted leading-snug">{workerStatus.schedule_hint}</div>
            </div>
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-end gap-3 border-t border-border/60 pt-4">
          <label className="min-w-[140px] text-[12px] font-semibold text-muted">
            Інтервал черги (сек)
            <input
              type="number"
              min={1}
              max={120}
              value={workerPoll}
              onChange={e => setWorkerPoll(Number(e.target.value))}
              className="mt-1.5 w-full rounded-xl border border-border/80 bg-surface px-3 py-2 text-[14px] text-ink outline-none focus:border-emerald"
            />
          </label>
          <label className="min-w-[140px] text-[12px] font-semibold text-muted">
            Sync каналів (сек)
            <input
              type="number"
              min={15}
              max={600}
              value={workerSync}
              onChange={e => setWorkerSync(Number(e.target.value))}
              className="mt-1.5 w-full rounded-xl border border-border/80 bg-surface px-3 py-2 text-[14px] text-ink outline-none focus:border-emerald"
            />
          </label>
          <button
            type="button"
            onClick={() => void saveWorkerDelays()}
            disabled={workerSaving}
            className="rounded-full border border-border/80 px-4 py-2.5 text-[12px] font-semibold text-ink hover:bg-surface disabled:opacity-60"
          >
            {workerSaving ? "Збереження…" : "Зберегти затримки"}
          </button>
          <button
            type="button"
            onClick={() => void loadWorkerStatus()}
            className="rounded-full px-3 py-2.5 text-[12px] font-semibold text-emerald hover:underline"
          >
            Оновити статус
          </button>
        </div>
        {!workerStatus?.telethon_configured && (
          <p className="mt-3 text-[11px] text-amber-800">
            TELETHON_API_ID / TELETHON_API_HASH не налаштовані в .env
          </p>
        )}
      </section>

      <form
        onSubmit={e => void handleAdd(e)}
        className="mb-6 flex flex-wrap items-end gap-3 rounded-2xl border border-border/70 bg-white p-4"
      >
        <label className="min-w-[180px] flex-1 text-[12px] font-semibold text-muted">
          Username або посилання
          <input
            value={username}
            onChange={e => setUsername(e.target.value)}
            placeholder="@ua_autobazar або t.me/..."
            className="mt-1.5 w-full rounded-xl border border-border/80 bg-surface px-3 py-2.5 text-[14px] text-ink outline-none focus:border-emerald"
          />
        </label>
        <label className="min-w-[140px] flex-1 text-[12px] font-semibold text-muted">
          Назва (опційно)
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Автобазар"
            className="mt-1.5 w-full rounded-xl border border-border/80 bg-surface px-3 py-2.5 text-[14px] text-ink outline-none focus:border-emerald"
          />
        </label>
        <button
          type="submit"
          disabled={adding || !username.trim()}
          className="rounded-full bg-emerald px-5 py-2.5 text-[13px] font-semibold text-white hover:bg-emerald-dark disabled:opacity-60"
        >
          {adding ? "Додаємо…" : "Додати канал"}
        </button>
      </form>

      <div className="grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
        <div className="space-y-2">
          {channels.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border/80 bg-white px-4 py-10 text-center text-[13px] text-muted">
              Немає каналів — додайте перший вище
            </div>
          ) : (
            channels.map(channel => {
              const active = selectedId === channel.id;
              return (
                <div
                  key={channel.id}
                  className={cn(
                    "rounded-2xl border bg-white p-4 transition-colors",
                    active ? "border-emerald shadow-sm" : "border-border/70 hover:border-emerald/40",
                  )}
                >
                  <button
                    type="button"
                    onClick={() => setSelectedId(channel.id)}
                    className="w-full text-left"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="text-[15px] font-bold text-ink">{channel.username}</div>
                        {channel.title && (
                          <div className="mt-0.5 text-[12px] text-muted">{channel.title}</div>
                        )}
                      </div>
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
                          channel.enabled
                            ? "bg-emerald-light text-emerald-dark"
                            : "bg-surface text-muted",
                        )}
                      >
                        {channel.enabled ? "ON" : "OFF"}
                      </span>
                    </div>
                    <div className="mt-2 text-[12px] text-muted">
                      {channel.listings_count.toLocaleString("uk-UA")} авто в базі
                    </div>
                  </button>
                  <div className="mt-3 flex gap-2">
                    <button
                      type="button"
                      onClick={() => void toggleEnabled(channel)}
                      className="rounded-lg border border-border/80 px-2.5 py-1.5 text-[11px] font-semibold text-ink hover:bg-surface"
                    >
                      {channel.enabled ? "Вимкнути" : "Увімкнути"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setPendingDelete(channel)}
                      className="rounded-lg border border-red-200 px-2.5 py-1.5 text-[11px] font-semibold text-red-600 hover:bg-red-50"
                    >
                      Видалити
                    </button>
                  </div>
                </div>
              );
            })
          )}
          <p className="px-1 pt-2 text-[11px] text-muted">
            Новий канал підтягує історію під час наступного планового циклу або після sync worker (інтервал вище).
            Realtime-пости — одразу, якщо процес telegram_worker запущений.
          </p>
        </div>

        <div className="rounded-2xl border border-border/70 bg-white p-4 sm:p-5">
          {!selected ? (
            <div className="py-16 text-center text-[13px] text-muted">
              Оберіть канал зліва, щоб побачити зібрані оголошення
            </div>
          ) : (
            <>
              <div className="mb-4 flex flex-wrap items-end justify-between gap-2 border-b border-border/60 pb-4">
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-[0.08em] text-muted">Канал</div>
                  <div className="mt-1 text-[18px] font-black text-ink">{selected.username}</div>
                  {selected.title && <div className="text-[13px] text-muted">{selected.title}</div>}
                </div>
                <a
                  href={
                    selected.username.includes("t.me/")
                      ? selected.username.startsWith("http")
                        ? selected.username
                        : `https://${selected.username.replace(/^\/\//, "")}`
                      : `https://t.me/${selected.username.replace(/^@/, "")}`
                  }
                  target="_blank"
                  rel="noreferrer"
                  className="text-[12px] font-semibold text-emerald hover:underline"
                >
                  Відкрити в Telegram →
                </a>
              </div>

              {listingsLoading ? (
                <div className="flex justify-center py-12">
                  <div className="h-7 w-7 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
                </div>
              ) : channelListings.length === 0 ? (
                <div className="py-12 text-center text-[13px] text-muted">
                  Ще немає оголошень з цього каналу
                </div>
              ) : (
                <div className="space-y-2">
                  {channelListings.map(item => {
                    const id = String(item.id ?? "");
                    const images = Array.isArray(item.images) ? (item.images as string[]) : [];
                    return (
                      <button
                        key={id}
                        type="button"
                        onClick={() => void openListing(id)}
                        disabled={detailLoadingId === id}
                        className="flex w-full items-center gap-3 rounded-xl border border-border/60 px-3 py-2.5 text-left transition-colors hover:border-emerald/40 hover:bg-surface/60 disabled:opacity-60"
                      >
                        <div className="relative h-14 w-20 shrink-0 overflow-hidden rounded-lg bg-surface">
                          {images[0] ? (
                            <Image src={images[0]} alt="" fill className="object-cover" unoptimized />
                          ) : null}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-[14px] font-semibold text-ink">
                            {String(item.title ?? "Без назви")}
                          </div>
                          <div className="mt-0.5 text-[12px] text-muted">
                            {formatPrice(item.price as number | undefined)}
                            {item.year ? ` · ${item.year}` : ""}
                            {item.region ? ` · ${String(item.region)}` : ""}
                          </div>
                          {item.found_at ? (
                            <div className="mt-0.5 text-[11px] text-muted/80">
                              {formatKyivDateTime(String(item.found_at))}
                            </div>
                          ) : null}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {selectedListing && (
        <ListingDetailModal listing={selectedListing} onClose={() => setSelectedListing(null)} />
      )}

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title={pendingDelete ? `Видалити ${pendingDelete.username}?` : ""}
        description="Оголошення в БД залишаться."
        confirmLabel="Видалити"
        cancelLabel="Скасувати"
        variant="danger"
        loading={deleting}
        onClose={() => {
          if (!deleting) setPendingDelete(null);
        }}
        onConfirm={() => {
          if (pendingDelete) void removeChannel(pendingDelete);
        }}
      />
    </div>
  );
}
