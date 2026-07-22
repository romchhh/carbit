"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  adminApi,
  type AdminActiveSearch,
  type AdminAnalytics,
  type AdminParseRun,
  type AdminParserNotification,
  type AdminParserSettings,
  type AdminParserStats,
  type AdminSearchDetail,
} from "@/lib/admin-api";
import { formatKyivDateTime } from "@/lib/datetime";
import { cn } from "@/lib/utils";

const STATUS_LABELS: Record<string, string> = {
  running: "В процесі",
  success: "Успішно",
  partial: "Частково",
  failed: "Помилка",
};

const SOURCE_LABELS: Record<string, string> = {
  auto_ria: "AUTO.RIA",
  olx: "OLX",
  telegram: "Telegram",
};

const TEST_SOURCES = [
  { key: "auto_ria" as const, label: "AUTO.RIA", className: "bg-blue-600 hover:bg-blue-700" },
  { key: "olx" as const, label: "OLX", className: "bg-orange-500 hover:bg-orange-600" },
  { key: "telegram" as const, label: "Telegram", className: "bg-sky-600 hover:bg-sky-700" },
];

function formatSource(source: string | null | undefined) {
  if (!source) return "—";
  return SOURCE_LABELS[source] ?? source.toUpperCase();
}

function formatPrice(price: number | null | undefined) {
  if (price == null) return "—";
  return `${price.toLocaleString("uk-UA")} грн`;
}

function formatSearchFilters(s: AdminActiveSearch) {
  const parts: string[] = [];
  if (s.brand) parts.push(s.brand);
  if (s.model) parts.push(s.model);
  if (s.region) parts.push(s.region);
  if (s.sources?.length) {
    parts.push(s.sources.map(src => SOURCE_LABELS[src] ?? src).join(", "));
  }
  return parts.length ? parts.join(" · ") : "Без фільтрів";
}

const TELEGRAM_ISSUE_LABELS: Record<string, string> = {
  no_bot_link: "Бот не підключено в кабінеті",
  bot_start_required: "Немає chat_id — натиснути /start у боті",
  not_attempted: "Ще не пробували відправити",
  send_failed: "Бот не доставив (заблоковано / помилка API)",
  skipped_duplicate_car: "Пропущено: це авто вже слали цьому юзеру",
  skipped_vin_mirror: "Пропущено: дзеркало з VIN",
};

function formatTelegramIssue(issue: string | null | undefined) {
  if (!issue) return null;
  return TELEGRAM_ISSUE_LABELS[issue] ?? issue;
}

export default function AdminParsingPage() {
  const [stats, setStats] = useState<AdminParserStats | null>(null);
  const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null);
  const [settings, setSettings] = useState<AdminParserSettings | null>(null);
  const [runs, setRuns] = useState<AdminParseRun[]>([]);
  const [listings, setListings] = useState<Array<Record<string, unknown>>>([]);
  const [notifications, setNotifications] = useState<AdminParserNotification[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedSearchIdForNotifications, setSelectedSearchIdForNotifications] = useState<
    string | null
  >(null);
  const [searchesPanelOpen, setSearchesPanelOpen] = useState(false);
  const [activeSearches, setActiveSearches] = useState<AdminActiveSearch[]>([]);
  const [selectedSearchId, setSelectedSearchId] = useState<string | null>(null);
  const [searchDetail, setSearchDetail] = useState<AdminSearchDetail | null>(null);
  const [loadingSearches, setLoadingSearches] = useState(false);
  const [loadingSearchDetail, setLoadingSearchDetail] = useState(false);
  const [deliverLoading, setDeliverLoading] = useState(false);
  const [deliverResult, setDeliverResult] = useState<string | null>(null);
  const [tgTestLoading, setTgTestLoading] = useState(false);
  const [tgTestResult, setTgTestResult] = useState<string | null>(null);
  const [manualTgId, setManualTgId] = useState("");
  const [manualTgSaving, setManualTgSaving] = useState(false);
  const [manualTgError, setManualTgError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingNotifications, setLoadingNotifications] = useState(false);
  const [running, setRunning] = useState(false);
  const [runningSource, setRunningSource] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadNotifications = useCallback(
    async (runId?: string | null, searchId?: string | null) => {
      setLoadingNotifications(true);
      try {
        const data = await adminApi.parserNotifications(
          50,
          runId ?? undefined,
          searchId ?? undefined,
        );
        setNotifications(data);
      } finally {
        setLoadingNotifications(false);
      }
    },
    [],
  );

  const loadActiveSearches = useCallback(async () => {
    setLoadingSearches(true);
    try {
      const data = await adminApi.parserSearches(true, 100);
      setActiveSearches(data);
    } finally {
      setLoadingSearches(false);
    }
  }, []);

  const loadSearchDetail = useCallback(async (searchId: string) => {
    setLoadingSearchDetail(true);
    try {
      const data = await adminApi.parserSearchDetail(searchId, 80);
      setSearchDetail(data);
    } finally {
      setLoadingSearchDetail(false);
    }
  }, []);

  const toggleActiveSearchesPanel = useCallback(async () => {
    if (searchesPanelOpen) {
      setSearchesPanelOpen(false);
      setSelectedSearchId(null);
      setSearchDetail(null);
      return;
    }
    setSearchesPanelOpen(true);
    await loadActiveSearches();
  }, [searchesPanelOpen, loadActiveSearches]);

  const selectSearch = useCallback(
    async (searchId: string) => {
      setSelectedSearchId(searchId);
      setSearchDetail(null);
      setManualTgId("");
      setManualTgError(null);
      setTgTestResult(null);
      setDeliverResult(null);
      await loadSearchDetail(searchId);
    },
    [loadSearchDetail],
  );

  const saveManualTelegramId = useCallback(
    async (userId: string, searchId: string) => {
      const id = manualTgId.trim();
      if (!id) {
        setManualTgError("Введіть chat_id");
        return;
      }
      setManualTgSaving(true);
      setManualTgError(null);
      try {
        await adminApi.userSetTelegramId(userId, id);
        setManualTgId("");
        await loadSearchDetail(searchId);
        await loadActiveSearches();
        setTgTestResult("Chat_id збережено");
      } catch (e) {
        setManualTgError(e instanceof Error ? e.message : "Помилка збереження");
      } finally {
        setManualTgSaving(false);
      }
    },
    [manualTgId, loadSearchDetail, loadActiveSearches],
  );

  const deliverTelegramForSearch = useCallback(async (searchId: string) => {
    setDeliverLoading(true);
    setDeliverResult(null);
    try {
      const res = await adminApi.parserSearchDeliverTelegram(searchId);
      setDeliverResult(`Відправлено: ${res.delivered}`);
      // Перезавантажити деталі пошуку
      await loadSearchDetail(searchId);
    } catch (e) {
      setDeliverResult(e instanceof Error ? e.message : "Помилка");
    } finally {
      setDeliverLoading(false);
    }
  }, [loadSearchDetail]);

  const testTelegramForUser = useCallback(async (userId: string) => {
    setTgTestLoading(true);
    setTgTestResult(null);
    try {
      const res = await adminApi.userTestTelegram(userId);
      setTgTestResult(res.sent ? `✅ Доставлено (chat ${res.chat_id_prefix})` : "❌ Не доставлено");
    } catch (e) {
      setTgTestResult(e instanceof Error ? e.message : "Помилка");
    } finally {
      setTgTestLoading(false);
    }
  }, []);

  const showTelegramForSearch = useCallback(
    (searchId: string) => {
      setSelectedRunId(null);
      setSelectedSearchIdForNotifications(searchId);
      void loadNotifications(null, searchId);
      document.getElementById("admin-telegram-notifications")?.scrollIntoView({ behavior: "smooth" });
    },
    [loadNotifications],
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [statsData, settingsData, runsData, listingsData, analyticsData] = await Promise.all([
        adminApi.parserStats(),
        adminApi.parserSettings(),
        adminApi.parserRuns(20),
        adminApi.parserListings(30),
        adminApi.analytics(),
      ]);
      setStats(statsData);
      setSettings(settingsData);
      setRuns(runsData);
      setListings(listingsData);
      setAnalytics(analyticsData);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadNotifications(selectedRunId, selectedSearchIdForNotifications);
  }, [selectedRunId, selectedSearchIdForNotifications, loadNotifications]);

  useEffect(() => {
    if (!searchesPanelOpen || activeSearches.length === 0) return;
    if (selectedSearchId) return;
    const first = activeSearches[0]?.id;
    if (first) {
      setSelectedSearchId(first);
      void loadSearchDetail(first);
    }
  }, [searchesPanelOpen, activeSearches, selectedSearchId, loadSearchDetail]);

  const handleRun = async () => {
    setRunning(true);
    setMessage(null);
    try {
      await adminApi.triggerParserRun();
      setMessage("Повний парсинг запущено");
      setSelectedRunId(null);
      setSelectedSearchIdForNotifications(null);
      await load();
      await loadNotifications(null, null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Помилка запуску");
    } finally {
      setRunning(false);
    }
  };

  const handleRunSource = async (source: "auto_ria" | "olx" | "telegram") => {
    setRunningSource(source);
    setMessage(null);
    try {
      await adminApi.triggerParserRunSource(source);
      setMessage(`Тестовий парсинг ${SOURCE_LABELS[source]} запущено`);
      setSelectedRunId(null);
      setSelectedSearchIdForNotifications(null);
      await load();
      await loadNotifications(null, null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Помилка запуску");
    } finally {
      setRunningSource(null);
    }
  };

  const handleSaveSettings = async () => {
    if (!settings) return;
    setSaving(true);
    setMessage(null);
    try {
      const updated = await adminApi.updateParserSettings(settings);
      setSettings(updated);
      setMessage("Налаштування збережено");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Помилка збереження");
    } finally {
      setSaving(false);
    }
  };

  const handleShowRunNotifications = (runId: string) => {
    setSelectedSearchIdForNotifications(null);
    setSelectedRunId(prev => (prev === runId ? null : runId));
  };

  const clearNotificationFilters = () => {
    setSelectedRunId(null);
    setSelectedSearchIdForNotifications(null);
  };

  if (loading && !stats) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="max-w-[1200px]">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-black text-ink">Парсинг</h1>
          <p className="mt-1 text-[13px] text-muted">
            AUTO.RIA · OLX · Telegram за збереженими фільтрами користувачів
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Link href="/admin/system" className="text-[12px] font-semibold text-emerald hover:underline">
            Стан системи →
          </Link>
          <Link href="/admin/channels" className="text-[12px] font-semibold text-emerald hover:underline">
            Telegram-канали →
          </Link>
          <button
            type="button"
            onClick={() => void handleRun()}
            disabled={running || runningSource !== null}
            className="rounded-full bg-emerald px-5 py-2.5 text-[13px] font-semibold text-white hover:bg-emerald-dark disabled:opacity-60"
          >
            {running ? "Запуск…" : "Запустити все"}
          </button>
          <div className="flex flex-wrap justify-end gap-2">
            {TEST_SOURCES.map(({ key, label, className }) => (
              <button
                key={key}
                type="button"
                onClick={() => void handleRunSource(key)}
                disabled={running || runningSource !== null}
                className={cn(
                  "rounded-full px-3.5 py-2 text-[12px] font-semibold text-white disabled:opacity-60",
                  className,
                )}
              >
                {runningSource === key ? "…" : label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {message && (
        <div className="mb-5 rounded-xl border border-emerald/20 bg-emerald-light/40 px-4 py-3 text-[13px] text-emerald-dark">
          {message}
        </div>
      )}

      <div className="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-6">
        {[
          {
            label: "Активних пошуків",
            value: stats?.active_searches ?? 0,
            clickable: true,
            onClick: () => void toggleActiveSearchesPanel(),
            active: searchesPanelOpen,
          },
          { label: "Звʼязків пошук–авто", value: stats?.total_search_listings ?? 0 },
          { label: "Оголошень у базі", value: stats?.total_listings ?? 0 },
          { label: "Дублів", value: analytics?.duplicate_listings ?? 0 },
          { label: "Telegram відправлено", value: stats?.total_telegram_sent ?? 0 },
          {
            label: "Останній запуск",
            value: stats?.last_run
              ? STATUS_LABELS[stats.last_run.status] ?? stats.last_run.status
              : "—",
          },
        ].map(({ label, value, clickable, onClick, active }) => {
          const inner = (
            <>
              <div className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</div>
              <div className="mt-1 text-[22px] font-bold text-ink">{value}</div>
              {clickable && (
                <div className="mt-1 text-[10px] font-semibold text-emerald">
                  {active ? "Згорнути список ↑" : "Переглянути →"}
                </div>
              )}
            </>
          );
          if (clickable && onClick) {
            return (
              <button
                key={label}
                type="button"
                onClick={onClick}
                className={cn(
                  "rounded-xl border bg-white px-4 py-4 text-left transition-colors hover:border-emerald/40 hover:bg-emerald/5",
                  active ? "border-emerald/50 ring-1 ring-emerald/20" : "border-border",
                )}
              >
                {inner}
              </button>
            );
          }
          return (
            <div key={label} className="rounded-xl border border-border bg-white px-4 py-4">
              {inner}
            </div>
          );
        })}
      </div>

      {searchesPanelOpen && (
        <div className="mb-8 rounded-2xl border border-emerald/30 bg-white p-5 shadow-sm">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-[16px] font-bold text-ink">Активні пошуки</h2>
              <p className="mt-1 text-[12px] text-muted">
                Знайдені авто в моніторингу та статус відправки в Telegram
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                setSearchesPanelOpen(false);
                setSelectedSearchId(null);
                setSearchDetail(null);
              }}
              className="rounded-full border border-border px-3 py-1.5 text-[12px] font-semibold hover:bg-surface"
            >
              Згорнути
            </button>
          </div>

          {loadingSearches && activeSearches.length === 0 ? (
            <div className="flex justify-center py-12">
              <div className="h-7 w-7 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
            </div>
          ) : activeSearches.length === 0 ? (
            <p className="text-[13px] text-muted">Немає активних пошуків</p>
          ) : (
            <div className="grid gap-4 lg:grid-cols-[minmax(0,340px)_1fr]">
              <div className="max-h-[560px] space-y-2 overflow-y-auto rounded-xl border border-border/70 bg-surface/30 p-2">
                {activeSearches.map(s => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => void selectSearch(s.id)}
                    className={cn(
                      "w-full rounded-lg border px-3 py-2.5 text-left transition-colors",
                      selectedSearchId === s.id
                        ? "border-emerald/50 bg-emerald/10"
                        : "border-transparent bg-white hover:border-border",
                    )}
                  >
                    <div className="text-[13px] font-semibold text-ink line-clamp-1">{s.name}</div>
                    <div className="mt-0.5 text-[11px] text-muted line-clamp-1">{formatSearchFilters(s)}</div>
                    <div className="mt-1.5 flex flex-wrap gap-1.5 text-[10px]">
                      <span className="rounded bg-ink/5 px-1.5 py-0.5 font-medium">
                        нових: {s.new_count}
                      </span>
                      <span className="rounded bg-ink/5 px-1.5 py-0.5 font-medium">
                        усього: {s.total_count}
                      </span>
                      <span className="rounded bg-emerald/15 px-1.5 py-0.5 font-medium text-emerald-dark">
                        TG: {s.telegram_sent_count}
                      </span>
                    </div>
                    <div className="mt-1 text-[10px] text-muted">
                      {s.user_name}
                      {s.telegram_connected ? (
                        <span className="ml-1 text-emerald-dark">· бот підключено</span>
                      ) : (
                        <span className="ml-1 text-amber-700">· бот не підключено</span>
                      )}
                    </div>
                  </button>
                ))}
              </div>

              <div className="min-h-[280px] rounded-xl border border-border/70 bg-surface/20 p-4">
                {loadingSearchDetail && !searchDetail && (
                  <div className="flex justify-center py-16">
                    <div className="h-7 w-7 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
                  </div>
                )}
                {searchDetail && (
                  <>
                    <div className="mb-4 flex flex-wrap items-start justify-between gap-3 border-b border-border/60 pb-3">
                      <div>
                        <h3 className="text-[15px] font-bold text-ink">{searchDetail.search.name}</h3>
                        <p className="mt-1 text-[12px] text-muted">{formatSearchFilters(searchDetail.search)}</p>
                        <p className="mt-1 text-[12px] text-muted">
                          {searchDetail.search.user_name} · {searchDetail.search.user_email}
                          {searchDetail.search.telegram_username && (
                            <> · @{searchDetail.search.telegram_username}</>
                          )}
                        </p>
                        <p className="mt-1 text-[11px]">
                          {searchDetail.search.telegram_connected &&
                          searchDetail.search.telegram_has_chat_id ? (
                            <span className="font-medium text-emerald-dark">
                              ✅ Telegram готовий до розсилки
                            </span>
                          ) : searchDetail.search.telegram_connected ? (
                            <span className="font-medium text-red-600">
                              ⚠️ Telegram підключено, але немає chat_id — потрібен /start у боті
                            </span>
                          ) : (
                            <span className="font-medium text-amber-800">
                              ⚠️ Telegram не підключено
                            </span>
                          )}
                        </p>
                        {!searchDetail.search.telegram_has_chat_id && (
                          <div className="mt-2 max-w-md rounded-lg border border-amber-200 bg-amber-50/80 p-2.5">
                            <p className="text-[11px] font-medium text-amber-900">
                              Вручну вставити Telegram chat_id
                            </p>
                            <div className="mt-1.5 flex flex-wrap items-center gap-2">
                              <input
                                type="text"
                                inputMode="numeric"
                                pattern="[0-9]*"
                                placeholder="напр. 123456789"
                                value={manualTgId}
                                onChange={e => setManualTgId(e.target.value)}
                                className="min-w-[140px] flex-1 rounded-lg border border-border bg-white px-2.5 py-1.5 text-[12px]"
                              />
                              <button
                                type="button"
                                disabled={manualTgSaving}
                                onClick={() =>
                                  void saveManualTelegramId(
                                    searchDetail.search.user_id,
                                    searchDetail.search.id,
                                  )
                                }
                                className="rounded-full bg-ink px-3 py-1.5 text-[11px] font-semibold text-white hover:bg-ink/90 disabled:opacity-60"
                              >
                                {manualTgSaving ? "…" : "Зберегти"}
                              </button>
                            </div>
                            {manualTgError && (
                              <p className="mt-1 text-[10px] text-red-600">{manualTgError}</p>
                            )}
                          </div>
                        )}
                        {searchDetail.search.last_checked_at && (
                          <p className="mt-1 text-[11px] text-muted">
                            Остання перевірка: {formatKyivDateTime(searchDetail.search.last_checked_at)}
                          </p>
                        )}
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <div className="text-[11px] text-muted">
                          Telegram відправлено:{" "}
                          <span className="font-bold text-ink">{searchDetail.telegram_sent_total}</span>
                          {searchDetail.telegram_pending > 0 && (
                            <span className="ml-2 text-amber-700">
                              очікує: {searchDetail.telegram_pending}
                            </span>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-2 justify-end">
                          {searchDetail.telegram_pending > 0 && (
                            <button
                              type="button"
                              onClick={() => void deliverTelegramForSearch(searchDetail.search.id)}
                              disabled={deliverLoading}
                              className="rounded-full bg-emerald px-3 py-1 text-[11px] font-semibold text-white hover:bg-emerald-dark disabled:opacity-60"
                            >
                              {deliverLoading ? "…" : `Надіслати (${searchDetail.telegram_pending})`}
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => void testTelegramForUser(searchDetail.search.user_id)}
                            disabled={tgTestLoading || !searchDetail.search.telegram_has_chat_id}
                            title={!searchDetail.search.telegram_has_chat_id ? "Немає chat_id" : "Тест"}
                            className="rounded-full border border-border px-3 py-1 text-[11px] font-semibold hover:bg-surface disabled:opacity-40"
                          >
                            {tgTestLoading ? "…" : "Тест Telegram"}
                          </button>
                        </div>
                        {(deliverResult || tgTestResult) && (
                          <div className="text-[11px] font-medium text-emerald-dark">
                            {deliverResult ?? tgTestResult}
                          </div>
                        )}
                        <button
                          type="button"
                          onClick={() => showTelegramForSearch(searchDetail.search.id)}
                          className="text-[11px] font-semibold text-emerald hover:underline"
                        >
                          Історія розсилки для цього пошуку ↓
                        </button>
                      </div>
                    </div>

                    <div className="max-h-[480px] space-y-2 overflow-y-auto">
                      {searchDetail.listings.length === 0 && (
                        <p className="text-[13px] text-muted">Поки немає привʼязаних оголошень</p>
                      )}
                      {searchDetail.listings.map(row => (
                        <div
                          key={row.listing_id}
                          className="flex gap-3 rounded-lg border border-border/60 bg-white p-2.5"
                        >
                          <div className="h-14 w-18 shrink-0 overflow-hidden rounded-md bg-ink/5 sm:h-16 sm:w-24">
                            {row.image ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img src={row.image} alt={row.title} className="h-full w-full object-cover" />
                            ) : (
                              <div className="flex h-full items-center justify-center text-[9px] text-muted">
                                —
                              </div>
                            )}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="text-[12px] font-semibold text-ink line-clamp-2">{row.title}</div>
                            <div className="mt-0.5 text-[11px] text-muted">
                              {formatSource(row.source)} · {row.year} ·{" "}
                              {row.price.toLocaleString("uk-UA")} {row.currency} · {row.region}
                            </div>
                            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                              {row.is_new && (
                                <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-800">
                                  NEW
                                </span>
                              )}
                              {row.telegram_sent ? (
                                <span className="rounded-full bg-emerald/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-dark">
                                  Telegram ✓
                                  {row.telegram_sent_at
                                    ? ` · ${formatKyivDateTime(row.telegram_sent_at)}`
                                    : ""}
                                </span>
                              ) : row.is_new ? (
                                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
                                  Telegram очікує
                                  {row.telegram_issue && formatTelegramIssue(row.telegram_issue) && (
                                    <span className="font-normal">
                                      {" "}
                                      · {formatTelegramIssue(row.telegram_issue)}
                                    </span>
                                  )}
                                </span>
                              ) : row.notified_at ? (
                                <span className="rounded-full bg-ink/5 px-2 py-0.5 text-[10px] font-medium text-muted">
                                  Telegram пропущено
                                </span>
                              ) : (
                                <span className="rounded-full bg-ink/5 px-2 py-0.5 text-[10px] font-medium text-muted">
                                  Без розсилки (базовий склад)
                                </span>
                              )}
                            </div>
                            {row.url && (
                              <a
                                href={row.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-1 inline-block text-[10px] font-semibold text-emerald hover:underline"
                              >
                                Оголошення →
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
                {!loadingSearchDetail && !searchDetail && selectedSearchId && (
                  <p className="text-[13px] text-muted">Не вдалося завантажити пошук</p>
                )}
                {!selectedSearchId && !loadingSearchDetail && (
                  <p className="text-[13px] text-muted">Оберіть пошук зі списку</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {analytics && (
        <div className="mb-8 rounded-2xl border border-border bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h2 className="text-[16px] font-bold text-ink">Розподіл за джерелами</h2>
            <Link href="/admin/listings" className="text-[12px] font-semibold text-emerald hover:underline">
              Усі оголошення →
            </Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {Object.entries(analytics.listings_by_source).map(([src, count]) => (
              <div key={src} className="rounded-xl border border-border/70 bg-surface/40 px-4 py-3">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                  {SOURCE_LABELS[src] ?? src}
                </div>
                <div className="mt-1 text-[22px] font-bold text-ink">{count.toLocaleString("uk-UA")}</div>
                <div className="text-[11px] text-muted">
                  +{analytics.listings_week} за тиждень (усі джерела)
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {settings && (
        <div className="mb-8 rounded-2xl border border-border bg-white p-5">
          <h2 className="text-[16px] font-bold text-ink">Налаштування</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="flex items-center gap-2 text-[13px]">
              <input
                type="checkbox"
                checked={settings.enabled}
                onChange={e => setSettings({ ...settings, enabled: e.target.checked })}
              />
              Автопарсинг увімкнено
            </label>
            <label className="flex items-center gap-2 text-[13px]">
              <input
                type="checkbox"
                checked={settings.notify_telegram}
                onChange={e => setSettings({ ...settings, notify_telegram: e.target.checked })}
              />
              Telegram-сповіщення
            </label>
            <label className="block text-[13px]">
              <span className="text-muted">Інтервал (сек)</span>
              <input
                type="number"
                min={60}
                max={86400}
                value={settings.interval_seconds}
                onChange={e => setSettings({ ...settings, interval_seconds: Number(e.target.value) })}
                className="mt-1 w-full rounded-lg border border-border px-3 py-2"
              />
            </label>
            <label className="block text-[13px]">
              <span className="text-muted">Макс. авто на групу фільтрів</span>
              <input
                type="number"
                min={5}
                max={100}
                value={settings.max_listings_per_group}
                onChange={e => setSettings({ ...settings, max_listings_per_group: Number(e.target.value) })}
                className="mt-1 w-full rounded-lg border border-border px-3 py-2"
              />
            </label>
            <label className="block text-[13px]">
              <span className="text-muted">Telegram worker: інтервал черги (сек)</span>
              <input
                type="number"
                min={1}
                max={120}
                value={settings.telegram_worker_poll_seconds ?? 3}
                onChange={e =>
                  setSettings({ ...settings, telegram_worker_poll_seconds: Number(e.target.value) })
                }
                className="mt-1 w-full rounded-lg border border-border px-3 py-2"
              />
              <span className="mt-1 block text-[11px] text-muted">
                Keyword/фото jobs, коли черга порожня. При активній черзі — ~0,5 с.
              </span>
            </label>
            <label className="block text-[13px]">
              <span className="text-muted">Telegram worker: sync каналів (сек)</span>
              <input
                type="number"
                min={15}
                max={600}
                value={settings.telegram_channel_sync_seconds ?? 45}
                onChange={e =>
                  setSettings({ ...settings, telegram_channel_sync_seconds: Number(e.target.value) })
                }
                className="mt-1 w-full rounded-lg border border-border px-3 py-2"
              />
            </label>
            <label className="block text-[13px]">
              <span className="text-muted">Telegram: глибина історії (повідомлень/канал)</span>
              <input
                type="number"
                min={10}
                max={3000}
                value={settings.telegram_history_limit ?? 500}
                onChange={e => setSettings({ ...settings, telegram_history_limit: Number(e.target.value) })}
                className="mt-1 w-full rounded-lg border border-border px-3 py-2"
              />
            </label>
            <label className="block text-[13px]">
              <span className="text-muted">Telegram: лише авто не старіші (год)</span>
              <input
                type="number"
                min={1}
                max={24}
                value={settings.notification_max_published_hours ?? 1}
                onChange={e =>
                  setSettings({
                    ...settings,
                    notification_max_published_hours: Number(e.target.value),
                  })
                }
                className="mt-1 w-full rounded-lg border border-border px-3 py-2"
              />
              <span className="mt-1 block text-[11px] text-muted">
                За замовчуванням 1 год. AUTO.RIA шукає з параметром top (за годину / 3 год).
              </span>
            </label>
            <label className="block text-[13px]">
              <span className="text-muted">TTL кешу пошуку (сек)</span>
              <input
                type="number"
                min={300}
                max={86400}
                value={settings.cache_ttl_seconds}
                onChange={e => setSettings({ ...settings, cache_ttl_seconds: Number(e.target.value) })}
                className="mt-1 w-full rounded-lg border border-border px-3 py-2"
              />
            </label>
            <label className="flex items-center gap-2 text-[13px]">
              <input
                type="checkbox"
                checked={settings.telegram_enabled}
                onChange={e => setSettings({ ...settings, telegram_enabled: e.target.checked })}
              />
              Парсинг Telegram-каналів
            </label>
          </div>
          <button
            type="button"
            onClick={() => void handleSaveSettings()}
            disabled={saving}
            className="mt-4 rounded-full border border-border px-4 py-2 text-[13px] font-semibold hover:bg-surface disabled:opacity-60"
          >
            {saving ? "Збереження…" : "Зберегти"}
          </button>
        </div>
      )}

      <div
        id="admin-telegram-notifications"
        className="mb-8 rounded-2xl border border-border bg-white p-5"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-[16px] font-bold text-ink">Telegram-розсилка</h2>
            <p className="mt-1 text-[12px] text-muted">
              Кому і яке авто було відправлено через бота
            </p>
          </div>
          {(selectedRunId || selectedSearchIdForNotifications) && (
            <button
              type="button"
              onClick={clearNotificationFilters}
              className="rounded-full border border-border px-3 py-1.5 text-[12px] font-semibold hover:bg-surface"
            >
              Показати всі
            </button>
          )}
        </div>

        {selectedRunId && (
          <div className="mt-3 rounded-lg bg-blue-50 px-3 py-2 text-[12px] text-blue-700">
            Фільтр за запуском від {formatKyivDateTime(runs.find(r => r.id === selectedRunId)?.started_at)}
          </div>
        )}
        {selectedSearchIdForNotifications && (
          <div className="mt-3 rounded-lg bg-emerald/10 px-3 py-2 text-[12px] text-emerald-dark">
            Фільтр за пошуком:{" "}
            <span className="font-semibold">
              {activeSearches.find(s => s.id === selectedSearchIdForNotifications)?.name ??
                searchDetail?.search.name ??
                selectedSearchIdForNotifications}
            </span>
          </div>
        )}

        <div className="mt-4 max-h-[520px] space-y-3 overflow-y-auto">
          {loadingNotifications && notifications.length === 0 && (
            <div className="flex justify-center py-8">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
            </div>
          )}
          {!loadingNotifications && notifications.length === 0 && (
            <p className="text-[13px] text-muted">Сповіщень ще не відправлялось</p>
          )}
          {notifications.map(item => (
            <div
              key={item.id}
              className="flex gap-3 rounded-xl border border-border/70 bg-surface/40 p-3 sm:gap-4"
            >
              <div className="h-16 w-20 shrink-0 overflow-hidden rounded-lg bg-ink/5 sm:h-20 sm:w-28">
                {item.listing_image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={item.listing_image}
                    alt={item.listing_title}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-[10px] text-muted">Без фото</div>
                )}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-[13px] font-semibold text-ink line-clamp-2">{item.listing_title}</div>
                    <div className="mt-1 text-[12px] text-muted">
                      {formatSource(item.listing_source)}
                      {item.listing_year ? ` · ${item.listing_year}` : ""}
                      {item.listing_price != null ? ` · ${formatPrice(item.listing_price)}` : ""}
                      {item.listing_region ? ` · ${item.listing_region}` : ""}
                    </div>
                  </div>
                  <div className="shrink-0 text-right text-[11px] text-muted">
                    {formatKyivDateTime(item.sent_at)}
                  </div>
                </div>

                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-emerald/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-dark">
                    {item.user_name}
                  </span>
                  <span className="text-[11px] text-muted">{item.user_email}</span>
                  {item.telegram_username && (
                    <span className="text-[11px] font-medium text-blue-600">@{item.telegram_username}</span>
                  )}
                </div>

                {item.search_name && (
                  <div className="mt-2 text-[11px] text-muted">
                    Пошук: <span className="font-medium text-ink">{item.search_name}</span>
                  </div>
                )}

                {item.listing_url && (
                  <a
                    href={item.listing_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-block text-[11px] font-semibold text-emerald hover:underline"
                  >
                    Відкрити оголошення →
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mb-8 grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-border bg-white p-5">
          <h2 className="text-[16px] font-bold text-ink">Логи запусків</h2>
          <div className="mt-4 max-h-[420px] space-y-3 overflow-y-auto">
            {runs.length === 0 && <p className="text-[13px] text-muted">Запусків ще не було</p>}
            {runs.map(run => (
              <div
                key={run.id}
                className={cn(
                  "rounded-xl border p-3",
                  selectedRunId === run.id ? "border-emerald/40 bg-emerald/5" : "border-border/70 bg-surface/50",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[12px] font-semibold text-ink">
                    {formatKyivDateTime(run.started_at)}
                  </span>
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase",
                      run.status === "success" && "bg-emerald/15 text-emerald-dark",
                      run.status === "failed" && "bg-red-100 text-red-600",
                      run.status === "partial" && "bg-amber-100 text-amber-700",
                      run.status === "running" && "bg-blue-100 text-blue-700",
                    )}
                  >
                    {STATUS_LABELS[run.status] ?? run.status}
                  </span>
                </div>
                <div className="mt-2 text-[12px] text-muted">
                  Груп: {run.filter_groups} · Пошуків: {run.searches_processed} · Знайдено: {run.listings_found} ·
                  Нових: {run.listings_new} · Telegram: {run.notifications_sent}
                </div>
                {run.notifications_sent > 0 && (
                  <button
                    type="button"
                    onClick={() => handleShowRunNotifications(run.id)}
                    className="mt-2 text-[11px] font-semibold text-emerald hover:underline"
                  >
                    {selectedRunId === run.id ? "Сховати розсилку цього запуску" : "Показати розсилку цього запуску"}
                  </button>
                )}
                {run.error && <p className="mt-1 text-[12px] text-red-600">{run.error}</p>}
                {run.log?.length > 0 && (
                  <pre className="mt-2 max-h-28 overflow-auto rounded-lg bg-ink/5 p-2 text-[11px] leading-relaxed text-ink/80">
                    {run.log.join("\n")}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-white p-5">
          <h2 className="text-[16px] font-bold text-ink">Останні оголошення</h2>
          <div className="mt-4 max-h-[420px] space-y-2 overflow-y-auto">
            {listings.length === 0 && <p className="text-[13px] text-muted">Оголошень ще немає</p>}
            {listings.map(item => (
              <div key={String(item.id)} className="rounded-xl border border-border/70 px-3 py-2.5">
                <div className="text-[13px] font-semibold text-ink line-clamp-1">{String(item.title)}</div>
                <div className="mt-0.5 text-[11px] text-muted">
                  {formatSource(String(item.source))} · {Number(item.price).toLocaleString("uk-UA")} грн · {String(item.region)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
