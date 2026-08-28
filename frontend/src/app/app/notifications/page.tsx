"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ListingCard } from "@/components/listings/ListingCard";
import { ListingDetailModal } from "@/components/listings/ListingDetailModal";
import { PriceDropNotificationCard } from "@/components/notifications/PriceDropNotificationCard";
import { useListingFavorites } from "@/hooks/useListingFavorite";
import { notifications as notificationsApi } from "@/lib/api";
import { notifyNotificationsChanged } from "@/lib/notifications-events";
import { saveRecentListing } from "@/lib/recent-listings";
import type { SortOption } from "@/lib/search-catalog";
import { AppEmpty, AppLoading, AppPage } from "@/components/layout/AppPage";
import type { Listing, Notification, NotificationStats, NotificationTypeFilter } from "@/types/api";
import { cn, timeAgo } from "@/lib/utils";

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "newest", label: "Спочатку нові" },
  { value: "published_asc", label: "Спочатку старі" },
  { value: "price_asc", label: "Спочатку дешеві" },
  { value: "price_desc", label: "Спочатку дорогі" },
  { value: "price_drop_desc", label: "За зниженням ціни" },
  { value: "year_desc", label: "За роком випуску" },
  { value: "mileage_asc", label: "За пробігом" },
];

type FilterKey = "all" | NotificationTypeFilter;

const FILTER_OPTIONS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "Усі" },
  { key: "listing_match", label: "Нові авто" },
  { key: "price_drop", label: "Зниження цін" },
  { key: "vin_found", label: "VIN" },
];

const PAGE_SIZE = 20;

function filterCount(stats: NotificationStats | null, key: FilterKey): number {
  if (!stats) return 0;
  if (key === "all") return stats.total;
  if (key === "price_drop") return stats.price_drops;
  if (key === "vin_found") return stats.vin_found;
  return stats.listing_matches;
}

export default function NotificationsPage() {
  const [items, setItems] = useState<Notification[]>([]);
  const [stats, setStats] = useState<NotificationStats | null>(null);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<FilterKey>("all");
  const [sort, setSort] = useState<SortOption>("newest");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);

  const listingItems = useMemo(
    () => items.filter((item): item is Notification & { listing: Listing } => Boolean(item.listing)),
    [items],
  );
  const otherItems = useMemo(() => items.filter(item => !item.listing), [items]);
  const listingIds = useMemo(() => listingItems.map(item => item.listing.id), [listingItems]);
  const { favoriteIds, loadingIds, error: favoriteError, clearError, toggleFavorite } =
    useListingFavorites(listingIds);

  const apiType = filter === "all" ? undefined : filter;

  const load = useCallback(async (nextFilter: FilterKey, nextSort: SortOption) => {
    setLoading(true);
    try {
      const [data, nextStats] = await Promise.all([
        notificationsApi.list(
          1,
          false,
          nextSort,
          PAGE_SIZE,
          nextFilter === "all" ? undefined : nextFilter,
        ),
        notificationsApi.stats(),
      ]);
      setStats(nextStats);
      setTotal(data.total);
      setPage(1);
      setHasMore(data.items.length > 0 && data.items.length < data.total);

      if (data.unread > 0) {
        setItems(data.items.map(item => ({ ...item, is_read: true })));
        void notificationsApi.markAllRead().then(() => notifyNotificationsChanged()).catch(() => {});
      } else {
        setItems(data.items);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const data = await notificationsApi.list(
        nextPage,
        false,
        sort,
        PAGE_SIZE,
        apiType,
      );
      setItems(prev => {
        const seen = new Set(prev.map(item => item.id));
        const next = [...prev];
        for (const item of data.items) {
          if (seen.has(item.id)) continue;
          seen.add(item.id);
          next.push(item);
        }
        return next;
      });
      setPage(nextPage);
      setHasMore(nextPage * PAGE_SIZE < data.total);
    } finally {
      setLoadingMore(false);
    }
  }, [apiType, hasMore, loadingMore, page, sort]);

  useEffect(() => {
    void load(filter, sort);
  }, [filter, sort, load]);

  const markOne = async (id: string) => {
    await notificationsApi.markRead(id);
    setItems(prev => prev.map(item => (item.id === id ? { ...item, is_read: true } : item)));
    notifyNotificationsChanged();
  };

  const markAll = async () => {
    await notificationsApi.markAllRead();
    setItems(prev => prev.map(item => ({ ...item, is_read: true })));
    notifyNotificationsChanged();
  };

  const openListing = async (notification: Notification, listing: Listing) => {
    saveRecentListing(listing);
    setSelectedListing(listing);
    if (!notification.is_read) {
      await markOne(notification.id);
    }
  };

  const seedDemo = async () => {
    setLoading(true);
    await notificationsApi.seedDemo();
    await load(filter, sort);
  };

  const unread = stats?.unread ?? 0;
  const priceDropCount = stats?.price_drops ?? 0;

  if (loading && items.length === 0) return <AppLoading />;

  return (
    <AppPage
      wide
      tourId="tour-section-notifications"
      title="Сповіщення"
      description={
        unread > 0
          ? `${unread} непрочитаних${stats?.unread_price_drops ? ` · ${stats.unread_price_drops} зі зниженням ціни` : ""}`
          : priceDropCount > 0
            ? `${priceDropCount} зі зниженням ціни в історії`
            : "Всі прочитані"
      }
      action={
        <div className="flex gap-2">
          {unread > 0 && (
            <Button variant="secondary" size="sm" onClick={() => void markAll()}>
              Прочитати все
            </Button>
          )}
          {items.length === 0 && (
            <Button variant="primary" size="sm" onClick={() => void seedDemo()}>
              Демо
            </Button>
          )}
        </div>
      }
    >
      {items.length === 0 && filter === "all" ? (
        <AppEmpty>
          <p className="text-muted">Сповіщень поки немає</p>
          <p className="mx-auto mt-2 max-w-sm text-[12px] text-muted/80">
            Створіть пошуковий запит — нові авто та зниження цін з&apos;являться тут і в Telegram.
          </p>
          <Link href="/app/dashboard" className="mt-6 flex justify-center">
            <Button variant="emerald" size="xl" className="w-full min-w-[min(100%,300px)] sm:w-auto sm:min-w-0">
              Створити моніторинг
            </Button>
          </Link>
        </AppEmpty>
      ) : (
        <>
          <div className="mb-4 space-y-3 rounded-2xl border border-border bg-white p-3.5 sm:px-5 sm:py-4 lg:mb-5 lg:px-6">
            <div className="flex flex-wrap gap-2">
              {FILTER_OPTIONS.map(option => {
                const count = filterCount(stats, option.key);
                const active = filter === option.key;
                const isPriceDrop = option.key === "price_drop";
                return (
                  <button
                    key={option.key}
                    type="button"
                    onClick={() => {
                      setFilter(option.key);
                      setPage(1);
                      if (option.key === "price_drop") setSort("price_drop_desc");
                    }}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12px] font-semibold transition-colors",
                      active
                        ? isPriceDrop
                          ? "border-rose-300 bg-rose-50 text-rose-800"
                          : "border-emerald bg-emerald text-white"
                        : isPriceDrop
                          ? "border-border bg-white text-muted hover:border-rose-200 hover:text-ink"
                          : "border-border bg-white text-muted hover:border-emerald/40 hover:text-ink",
                    )}
                  >
                    {option.label}
                    {count > 0 ? (
                      <span
                        className={cn(
                          "rounded-full px-1.5 py-0.5 text-[10px] font-bold",
                          active
                            ? isPriceDrop
                              ? "bg-rose-600 text-white"
                              : "bg-white/20 text-white"
                            : "bg-surface text-ink",
                        )}
                      >
                        {count}
                      </span>
                    ) : null}
                  </button>
                );
              })}
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="text-[13px] text-muted lg:text-[14px]">
                {total} {total === 1 ? "сповіщення" : total < 5 ? "сповіщення" : "сповіщень"}
                {items.length < total ? (
                  <span className="ml-1.5 text-muted/80">· показано {items.length}</span>
                ) : null}
              </div>
              <label className="flex items-center gap-2 text-[13px] lg:text-[14px]">
                <span className="text-muted">Сортування</span>
                <select
                  value={sort}
                  onChange={e => setSort(e.target.value as SortOption)}
                  className="rounded-lg border border-border bg-white px-3 py-2 text-[13px] font-medium text-ink lg:px-3.5 lg:py-2.5 lg:text-[14px]"
                >
                  {SORT_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          {items.length === 0 ? (
            <AppEmpty>
              <p className="text-muted">
                {filter === "price_drop" ? "Знижень ціни поки немає" : "У цій категорії сповіщень немає"}
              </p>
              {filter === "price_drop" ? (
                <p className="mx-auto mt-2 max-w-sm text-[12px] text-muted/80">
                  Коли ціна авто з моніторингу впаде на ≥5%, ви отримаєте сповіщення тут і в Telegram.
                </p>
              ) : null}
            </AppEmpty>
          ) : (
            <div className="-mx-1 flex flex-col gap-3 px-1 sm:mx-0 sm:gap-3 sm:px-0 lg:gap-4">
              {listingItems.map(item =>
                item.type === "price_drop" ? (
                  <div key={item.id} className="relative">
                    {!item.is_read ? (
                      <span
                        className="absolute right-3 top-3 z-10 h-2.5 w-2.5 rounded-full bg-rose-500 ring-2 ring-white"
                        aria-hidden
                      />
                    ) : null}
                    <PriceDropNotificationCard
                      notification={item}
                      onOpen={() => void openListing(item, item.listing)}
                      isFavorite={favoriteIds.has(item.listing.id)}
                      favoriteLoading={loadingIds.has(item.listing.id)}
                      onToggleFavorite={() => void toggleFavorite(item.listing)}
                      className={cn(!item.is_read && "shadow-[0_8px_28px_-10px_rgba(225,29,46,0.28)]")}
                    />
                  </div>
                ) : (
                  <div key={item.id} className="relative">
                    {!item.is_read && (
                      <span
                        className="absolute left-3 top-3 z-10 h-2.5 w-2.5 rounded-full bg-emerald ring-2 ring-white sm:left-[calc(13rem+1rem)] lg:left-[calc(22rem+1.5rem)] lg:h-3 lg:w-3"
                        aria-hidden
                      />
                    )}
                    <ListingCard
                      listing={item.listing}
                      onClick={() => void openListing(item, item.listing)}
                      className={cn(
                        !item.is_read && "border-emerald/30 shadow-[0_4px_20px_-8px_rgba(16,185,129,0.35)]",
                      )}
                      isFavorite={favoriteIds.has(item.listing.id)}
                      favoriteLoading={loadingIds.has(item.listing.id)}
                      onToggleFavorite={() => void toggleFavorite(item.listing)}
                    />
                    <div className="mt-1.5 flex flex-wrap items-center gap-2 px-1 text-[11px] text-muted lg:mt-2 lg:gap-2.5 lg:text-[13px]">
                      {item.type === "vin_found" && <Badge variant="outline">VIN</Badge>}
                      {item.type === "listing_match" && <Badge variant="emerald">Нове авто</Badge>}
                      {item.sent_telegram && <Badge variant="outline">Telegram</Badge>}
                      {item.body && item.type !== "listing_match" ? (
                        <span className="text-muted">{item.body}</span>
                      ) : null}
                      <span>{timeAgo(item.created_at)}</span>
                    </div>
                  </div>
                ),
              )}

              {otherItems.map(item => (
                <div
                  key={item.id}
                  className={cn(
                    "rounded-2xl border bg-white p-4 lg:rounded-[1.25rem] lg:p-6",
                    item.is_read ? "border-border opacity-80" : "border-emerald/20 bg-emerald-light/10",
                  )}
                >
                  <div className="flex items-start justify-between gap-3 lg:gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[14px] font-semibold text-ink lg:text-[17px]">{item.title}</span>
                        {!item.is_read && (
                          <span className="h-2 w-2 shrink-0 rounded-full bg-emerald lg:h-2.5 lg:w-2.5" />
                        )}
                      </div>
                      <p className="mt-1 text-[12px] leading-relaxed text-muted lg:mt-2 lg:text-[14px]">{item.body}</p>
                      <div className="mt-2 flex items-center gap-2 lg:mt-3">
                        {item.sent_telegram && <Badge variant="outline">Telegram</Badge>}
                        <span className="text-[11px] text-muted lg:text-[12px]">{timeAgo(item.created_at)}</span>
                      </div>
                    </div>
                    {!item.is_read && (
                      <button
                        type="button"
                        onClick={() => void markOne(item.id)}
                        className="shrink-0 text-[12px] font-semibold text-emerald-dark hover:underline lg:text-[13px]"
                      >
                        Прочитати
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {hasMore && (
            <button
              type="button"
              onClick={() => void loadMore()}
              disabled={loadingMore}
              className="mt-6 w-full rounded-2xl bg-emerald py-3.5 text-[14px] font-semibold text-white shadow-md shadow-emerald/25 transition-colors hover:bg-emerald-dark disabled:opacity-60"
            >
              {loadingMore ? "Завантаження..." : `Показати ще (${Math.min(PAGE_SIZE, total - items.length)})`}
            </button>
          )}
        </>
      )}

      <ListingDetailModal
        listing={selectedListing}
        onClose={() => {
          clearError();
          setSelectedListing(null);
        }}
        isFavorite={selectedListing ? favoriteIds.has(selectedListing.id) : false}
        favoriteLoading={selectedListing ? loadingIds.has(selectedListing.id) : false}
        onToggleFavorite={
          selectedListing ? () => void toggleFavorite(selectedListing) : undefined
        }
        favoriteError={favoriteError}
      />
    </AppPage>
  );
}
