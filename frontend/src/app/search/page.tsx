"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthGateModal } from "@/components/auth/AuthGateModal";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { RecentListingsSection } from "@/components/listings/RecentListingsSection";
import { DesktopSearchMonitorFab } from "@/components/search/DesktopSearchMonitorFab";
import { MobileSearchFiltersFab } from "@/components/search/MobileSearchFiltersFab";
import { RecentSearchesSection } from "@/components/search/RecentSearchesSection";
import { SearchDesktopSplit } from "@/components/search/SearchDesktopSplit";
import { SearchFiltersPanel } from "@/components/search/SearchFiltersPanel";
import { SearchPreviewResults } from "@/components/search/SearchPreviewResults";
import { TelegramConnectPrompt } from "@/components/search/TelegramConnectPrompt";
import { useAuth } from "@/contexts/AuthProvider";
import { usePreviewSearch } from "@/hooks/usePreviewSearch";
import { useRecentSearches } from "@/hooks/useRecentSearches";
import { useSaveSearch } from "@/hooks/useSaveSearch";
import { isGuestSearchLimitError, searches as searchesApi } from "@/lib/api";
import {
  DEFAULT_FILTERS,
  normalizePriceRange,
  normalizeYearRange,
  type SearchFilterState,
} from "@/lib/search-catalog";
import {
  beginSearchDraftAutoRun,
  peekSearchDraft,
  saveSearchDraft,
} from "@/lib/search-draft";
import { findMatchingSearch } from "@/lib/search-filters-api";
import {
  canGuestSearch,
  getGuestSearchesRemaining,
  GUEST_SEARCH_LIMIT,
} from "@/lib/guest-search";
import type { SearchQuery } from "@/types/api";

const PUBLIC_SEARCH_DEFAULTS: SearchFilterState = {
  ...DEFAULT_FILTERS,
  region: "Вся Україна",
  regions: [],
  currency: "USD",
};

export default function PublicSearchPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const isGuest = !user;
  const [authOpen, setAuthOpen] = useState(false);
  const [authReason, setAuthReason] = useState<"limit" | "manual">("manual");
  const [remaining, setRemaining] = useState(getGuestSearchesRemaining);
  const [guestReady, setGuestReady] = useState(false);
  const [searches, setSearches] = useState<SearchQuery[]>([]);
  const [tgPromptOpen, setTgPromptOpen] = useState(false);
  const autoRan = useRef(false);
  const filtersPanelRef = useRef<HTMLDivElement>(null);

  const { saveSearch, saving, saveSuccess, saveError, saveLimitReached, clearSaveMessages } =
    useSaveSearch(created => {
      setSearches(prev => [created, ...prev.filter(s => s.id !== created.id)]);
    });

  const {
    filters,
    setFilters,
    results,
    total,
    marketTotal,
    page,
    pages,
    sort,
    freshness,
    running,
    searching,
    loadingMore,
    hasMore,
    error,
    errorRetryAfter,
    sourceStatuses,
    partial,
    fromCache,
    resultsRef,
    runSearch,
    changeSort,
    changeFreshness,
    loadMore,
    reset,
    clearError,
    restoreFromRecentCache,
  } = usePreviewSearch(PUBLIC_SEARCH_DEFAULTS, { guest: true });

  const matchingMonitor = useMemo(
    () => (user ? findMatchingSearch(searches, filters) : null),
    [user, searches, filters],
  );

  const { trackSearchStart, handleRecentSelect } = useRecentSearches({
    filters,
    freshness,
    sort,
    pages,
    total,
    marketTotal,
    searching,
    results,
    setFilters,
    changeFreshness,
    runSearch,
    restoreFromRecentCache,
    scrollTargetRef: filtersPanelRef,
    onBeforeSelect: () => {
      clearSaveMessages();
      clearError();
    },
  });

  useEffect(() => {
    if (!user) {
      setSearches([]);
      return;
    }
    searchesApi
      .list()
      .then(setSearches)
      .catch(() => setSearches([]));
  }, [user]);

  useEffect(() => {
    if (!isGuest) {
      setGuestReady(true);
      return;
    }
    let cancelled = false;
    void fetch("/api/guest-search/init", { credentials: "include" })
      .then(res => {
        if (!cancelled && res.ok) setGuestReady(true);
      })
      .catch(() => {
        if (!cancelled) setGuestReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, [isGuest]);

  useEffect(() => {
    const draft = peekSearchDraft();
    if (draft) {
      setFilters(draft.filters);
      changeFreshness(draft.freshness);
    }
  }, [changeFreshness, setFilters]);

  useEffect(() => {
    if (loading || !guestReady || autoRan.current) return;
    if (isGuest && !canGuestSearch()) {
      setAuthReason("limit");
      setAuthOpen(true);
      return;
    }
    const draft = peekSearchDraft();
    if (!draft || !beginSearchDraftAutoRun()) return;
    autoRan.current = true;
    trackSearchStart(draft.filters, draft.freshness);
    void runSearch(draft.filters, draft.freshness);
  }, [guestReady, isGuest, loading, runSearch, trackSearchStart]);

  useEffect(() => {
    if (error && isGuestSearchLimitError(error)) {
      setAuthReason("limit");
      setAuthOpen(true);
    }
  }, [error]);

  useEffect(() => {
    if (isGuest) setRemaining(getGuestSearchesRemaining());
  }, [isGuest, running, searching, total]);

  const openAuth = (reason: "limit" | "manual" = "manual") => {
    setAuthReason(reason);
    setAuthOpen(true);
  };

  const handleSearch = (
    overrideFilters?: SearchFilterState,
    overrideSort?: Parameters<typeof runSearch>[2],
  ) => {
    if (isGuest && !canGuestSearch()) {
      openAuth("limit");
      return;
    }
    clearSaveMessages();
    clearError();
    const nextFilters = overrideFilters ?? filters;
    const years = normalizeYearRange(nextFilters.yearFrom, nextFilters.yearTo);
    const prices = normalizePriceRange(nextFilters.priceFrom, nextFilters.priceTo);
    const sanitized = {
      ...nextFilters,
      yearFrom: years.from,
      yearTo: years.to,
      priceFrom: prices.from,
      priceTo: prices.to,
    };
    setFilters(sanitized);
    saveSearchDraft(sanitized, { freshness });
    trackSearchStart(sanitized, freshness);
    void runSearch(sanitized, freshness, overrideSort);
  };

  const handleReset = () => {
    clearSaveMessages();
    reset();
    setFilters({ ...PUBLIC_SEARCH_DEFAULTS });
    changeFreshness("all");
  };

  const handleSave = () => {
    void saveSearch(filters, results);
  };

  const handleMonitorClick = () => {
    if (isGuest) {
      router.push(`/auth/login?redirect=${encodeURIComponent("/search")}`);
      return;
    }
    if (saving || saveLimitReached) return;
    if (matchingMonitor) {
      router.push(`/app/monitors/${matchingMonitor.id}`);
      return;
    }
    if (!user?.telegram_connected) {
      setTgPromptOpen(true);
      return;
    }
    handleSave();
  };

  const handleAuthenticated = () => {
    setAuthOpen(false);
    window.location.reload();
  };

  const displayError = error && !isGuestSearchLimitError(error) ? error : null;

  const renderFiltersPanel = (options?: { inModal?: boolean; onClose?: () => void }) => (
    <SearchFiltersPanel
      wide
      variant="sidebar"
      inModal={options?.inModal}
      filters={filters}
      onChange={setFilters}
      onReset={handleReset}
      onSearch={(overrideFilters, overrideSort) => {
        handleSearch(overrideFilters, overrideSort);
        options?.onClose?.();
      }}
      onSortChange={changeSort}
      onSave={user ? handleSave : undefined}
      searching={searching}
      searchError={displayError}
      searchErrorRetryAfter={errorRetryAfter}
      saving={saving}
      saveSuccess={saveSuccess}
      saveError={saveError}
      saveLimitReached={saveLimitReached}
      telegramConnected={user?.telegram_connected}
      monitorConnected={Boolean(matchingMonitor)}
      connectedMonitorId={matchingMonitor?.id ?? null}
      freshness={freshness}
      onFreshnessChange={changeFreshness}
      pricePlaceholderFrom="Від"
      pricePlaceholderTo="До"
      monitorSlot={
        options?.inModal ? null : (
          <DesktopSearchMonitorFab
            connected={Boolean(matchingMonitor)}
            connectedMonitorId={matchingMonitor?.id ?? null}
            saving={saving}
            limitReached={saveLimitReached}
            onSave={handleMonitorClick}
          />
        )
      }
    />
  );

  const resultsPanel = (
    <SearchPreviewResults
      resultsRef={resultsRef}
      running={running}
      searching={searching}
      loadingMore={loadingMore}
      hasMore={hasMore}
      total={total}
      marketTotal={marketTotal}
      results={results}
      sort={sort}
      freshness={freshness}
      error={displayError}
      sourceStatuses={sourceStatuses}
      partial={partial}
      fromCache={fromCache}
      onSortChange={changeSort}
      onFreshnessChange={changeFreshness}
      onLoadMore={loadMore}
    />
  );

  return (
    <>
      <Header />
      <main className="min-h-[70dvh] bg-[#eef0f4] pt-[72px] sm:pt-[80px] lg:bg-canvas">
        <div className="mx-auto w-full max-w-[1440px] px-2.5 py-4 sm:px-4 sm:py-6 lg:px-6 lg:py-8">
          <div className="lg:rounded-[28px] lg:border lg:border-border/50 lg:bg-white lg:p-5 lg:shadow-island xl:p-6">
            <div className="lg:max-w-none pb-24 lg:pb-0">
              <div className="mb-5 flex flex-col gap-2 sm:mb-7 sm:flex-row sm:items-start sm:justify-between sm:gap-3 lg:mb-6">
                <div>
                  <h1 className="text-[22px] font-black tracking-[-0.02em] text-ink sm:text-[26px]">
                    Пошук авто
                  </h1>
                  <p className="mt-1 max-w-[560px] text-[12px] leading-relaxed text-muted sm:text-[13px]">
                    {isGuest ? (
                      <>
                        AUTO.RIA, OLX і Telegram в одному пошуку. Безкоштовно — {GUEST_SEARCH_LIMIT}{" "}
                        пошуки без реєстрації.
                      </>
                    ) : (
                      <>AUTO.RIA, OLX і Telegram в одному пошуку — усі авто або лише свіжі за тиждень.</>
                    )}
                  </p>
                </div>
                <span className="flex w-fit flex-col items-start gap-1 sm:items-end">
                  {isGuest ? (
                    <>
                      <span className="rounded-lg border border-emerald/25 bg-emerald/10 px-3 py-1.5 text-[11px] font-semibold text-emerald-dark sm:text-[12px]">
                        Залишилось {remaining} з {GUEST_SEARCH_LIMIT} безкоштовних пошуків
                      </span>
                      <button
                        type="button"
                        onClick={() => openAuth("manual")}
                        className="text-[11px] font-semibold text-emerald-dark hover:underline"
                      >
                        Увійти / зареєструватись →
                      </button>
                    </>
                  ) : (
                    <>
                      <span className="rounded-lg border border-border bg-surface px-3 py-1.5 text-[11px] text-muted sm:bg-white sm:text-[12px]">
                        До <strong className="text-ink">{user?.searches_limit ?? "—"}</strong> збережених
                        моніторингів
                      </span>
                      <Link
                        href="/app/billing"
                        className="text-[11px] font-semibold text-emerald-dark hover:underline"
                      >
                        {user?.plan === "free" ? "Оформити підписку →" : "Змінити тариф →"}
                      </Link>
                    </>
                  )}
                </span>
              </div>

              <SearchDesktopSplit
                filtersRef={filtersPanelRef}
                filters={renderFiltersPanel()}
                results={resultsPanel}
                filtersMobileHidden
              />

              <div className="mt-10 space-y-10">
                <RecentSearchesSection onSelect={handleRecentSelect} />
                <RecentListingsSection />
              </div>

              <MobileSearchFiltersFab
                targetRef={filtersPanelRef}
                pinned
                bottomInset="public"
                renderFilters={close => renderFiltersPanel({ inModal: true, onClose: close })}
                monitor={{
                  onClick: handleMonitorClick,
                  saving,
                  disabled: saveLimitReached,
                  connected: Boolean(matchingMonitor),
                  label: "Підключити моніторинг",
                }}
              />
            </div>
          </div>
        </div>
      </main>
      <Footer />

      {!loading && isGuest && (
        <AuthGateModal
          open={authOpen}
          onClose={() => setAuthOpen(false)}
          onAuthenticated={handleAuthenticated}
          headline={
            authReason === "limit"
              ? "Безкоштовні пошуки вичерпано"
              : "Увійдіть, щоб зберегти пошук"
          }
          description={
            authReason === "limit"
              ? `Ви використали ${GUEST_SEARCH_LIMIT} безкоштовних пошуки. Зареєструйтесь — 7 днів безкоштовно, моніторинг і сповіщення в Telegram.`
              : "Створіть акаунт за хвилину — збережіть фільтри, підключіть моніторинг і отримуйте нові авто в Telegram."
          }
        />
      )}

      {user && (
        <TelegramConnectPrompt
          open={tgPromptOpen}
          onClose={() => setTgPromptOpen(false)}
          onContinueWithoutTelegram={handleSave}
          onConnected={handleSave}
        />
      )}
    </>
  );
}
