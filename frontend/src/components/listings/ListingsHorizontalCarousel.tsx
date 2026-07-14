"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ListingDetailModal } from "@/components/listings/ListingDetailModal";
import { ListingFavoriteButton } from "@/components/listings/ListingFavoriteButton";
import { Badge } from "@/components/ui/Badge";
import { IconArrowLeft, IconArrowRight } from "@/components/icons";
import { useListingFavorites } from "@/hooks/useListingFavorite";
import { saveRecentListing } from "@/lib/recent-listings";
import { SourceBadge } from "@/components/listings/SourceBadge";
import { SourceLinks } from "@/components/listings/SourceLinks";
import { PublishedTimeBadge } from "@/components/listings/PublishedTimeBadge";
import { cn, formatMileage, publishedAgoLabel } from "@/lib/utils";
import { formatListingPrice, resolveDisplayCurrency } from "@/lib/display-currency";
import { useAuth } from "@/contexts/AuthProvider";
import type { Listing } from "@/types/api";

type Props = {
  listings: Listing[];
  loading?: boolean;
  error?: string | null;
  title?: string;
  description?: string;
  linkHref?: string;
  linkLabel?: string;
  embedded?: boolean;
  canFavorite?: boolean;
  showNewBadge?: boolean;
  className?: string;
  id?: string;
};

function isRecentListing(listing: Listing) {
  const published = new Date(listing.published_at).getTime();
  if (Number.isNaN(published)) return false;
  return Date.now() - published < 24 * 60 * 60 * 1000;
}

export function ListingsHorizontalCarousel({
  listings,
  loading = false,
  error = null,
  title,
  description,
  linkHref,
  linkLabel,
  embedded = false,
  canFavorite = true,
  showNewBadge = false,
  className,
  id,
}: Props) {
  const { user } = useAuth();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const { favoriteIds, loadingIds, error: favoriteError, clearError, toggleFavorite } = useListingFavorites(
    canFavorite ? listings.map(item => item.id) : [],
  );

  const scrollToIndex = useCallback((index: number) => {
    const container = scrollRef.current;
    if (!container) return;

    const card = container.children[index] as HTMLElement | undefined;
    if (!card) return;

    container.scrollTo({ left: card.offsetLeft, behavior: "smooth" });
    setActiveIndex(index);
  }, []);

  useEffect(() => {
    const container = scrollRef.current;
    if (!container || listings.length === 0) return;

    const cards = Array.from(container.children) as HTMLElement[];
    const observer = new IntersectionObserver(
      entries => {
        const visible = entries
          .filter(entry => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

        if (!visible.length) return;

        const index = cards.indexOf(visible[0].target as HTMLElement);
        if (index >= 0) setActiveIndex(index);
      },
      { root: container, threshold: 0.55 },
    );

    cards.forEach(card => observer.observe(card));
    return () => observer.disconnect();
  }, [listings]);

  useEffect(() => {
    if (activeIndex >= listings.length) {
      setActiveIndex(Math.max(0, listings.length - 1));
    }
  }, [activeIndex, listings.length]);

  const openListing = (listing: Listing) => {
    saveRecentListing(listing);
    setSelectedListing(listing);
  };

  const canPrev = activeIndex > 0;
  const canNext = activeIndex < listings.length - 1;
  const hasHeader = Boolean(title || description || linkHref);
  const showControls = !loading && !error && listings.length > 1;

  if (!loading && !error && listings.length === 0) {
    return null;
  }

  const headerPad = embedded ? "px-0 sm:px-0" : "px-5 sm:px-6";
  const trackPad = embedded
    ? "pl-0 pr-4 -mr-4 sm:pl-0 sm:pr-0 sm:mr-0"
    : "-mx-5 pl-5 pr-8 sm:-mx-6 sm:px-6";
  const controlsPad = embedded ? "px-0 sm:px-0" : "px-5 sm:px-6";

  return (
    <>
      <section id={id} className={cn("overflow-x-hidden", className)}>
        {hasHeader && (
          <div className={cn("mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between", headerPad)}>
            <div>
              {title && (
                <h2
                  className={cn(
                    "font-semibold leading-tight tracking-[-0.02em] text-ink",
                    embedded ? "text-[17px] font-bold" : "text-[26px] sm:text-[32px]",
                  )}
                >
                  {title}
                </h2>
              )}
              {description && (
                <p
                  className={cn(
                    "mt-1 max-w-[420px] leading-snug text-muted",
                    embedded ? "text-[13px]" : "text-[13px] sm:text-[14px]",
                  )}
                >
                  {description}
                </p>
              )}
            </div>
            {linkHref && linkLabel && !error && (
              <Link
                href={linkHref}
                className="inline-flex shrink-0 items-center gap-1.5 text-[12px] font-medium text-muted transition-colors hover:text-emerald-dark"
              >
                {linkLabel}
                <span className="text-emerald">→</span>
              </Link>
            )}
          </div>
        )}

        {loading ? (
          <div className={cn("flex gap-3 overflow-hidden pb-2 sm:gap-4", trackPad)}>
            {Array.from({ length: 4 }).map((_, index) => (
              <div
                key={index}
                className="h-[280px] w-[272px] shrink-0 animate-pulse rounded-2xl border border-border/70 bg-surface sm:w-[300px]"
              />
            ))}
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-border/70 bg-surface/50 px-5 py-10 text-center sm:px-6 sm:py-12">
            <p className="text-[15px] font-semibold text-ink">{error}</p>
          </div>
        ) : (
          <>
            <div
              ref={scrollRef}
              className={cn(
                "flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2 scroll-smooth scrollbar-hide sm:gap-4",
                trackPad,
              )}
            >
              {listings.map(listing => {
                const city = listing.region.split(",")[0]?.trim() || listing.region;
                const fuel = listing.fuel.split(",")[0]?.trim();

                return (
                  <article
                    key={listing.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => openListing(listing)}
                    onKeyDown={e => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        openListing(listing);
                      }
                    }}
                    className="w-[272px] shrink-0 snap-start overflow-hidden rounded-2xl border border-border/70 bg-white text-left transition-all hover:border-emerald/30 hover:shadow-[0_8px_24px_-10px_rgba(10,12,14,0.16)] sm:w-[300px]"
                  >
                    <div className="relative h-[152px] bg-surface sm:h-[168px]">
                      {listing.images[0] ? (
                        <Image
                          src={listing.images[0]}
                          alt={listing.title}
                          fill
                          className="object-cover"
                          sizes="300px"
                          unoptimized
                        />
                      ) : (
                        <div className="flex h-full items-center justify-center text-[13px] text-muted">
                          Без фото
                        </div>
                      )}
                      <div className="absolute inset-x-0 top-0 flex items-start justify-between gap-2 p-2.5">
                        <div className="flex flex-wrap gap-1">
                          {showNewBadge && isRecentListing(listing) && (
                            <Badge variant="emerald" className="px-2 py-0.5 text-[10px]">
                              Нове
                            </Badge>
                          )}
                        </div>
                        {canFavorite && (
                          <ListingFavoriteButton
                            active={favoriteIds.has(listing.id)}
                            loading={loadingIds.has(listing.id)}
                            onToggle={() => toggleFavorite(listing)}
                            variant="overlay"
                          />
                        )}
                      </div>
                      <div className="absolute bottom-2 left-2">
                        <PublishedTimeBadge date={listing.published_at} short />
                      </div>
                    </div>

                    <div className="p-4">
                      <h3 className="truncate text-[15px] font-semibold leading-tight text-ink">
                        {listing.title}
                      </h3>
                      <p className="mt-2 text-[20px] font-semibold tracking-tight text-ink">
                        {formatListingPrice(
                          listing.price,
                          listing.currency,
                          resolveDisplayCurrency(user?.preferred_currency),
                          listing.source_data,
                        )}
                      </p>
                      <p className="mt-1.5 text-[12px] leading-snug text-muted">
                        {[
                          listing.year > 0 ? String(listing.year) : null,
                          listing.mileage > 0 ? formatMileage(listing.mileage) : null,
                          listing.transmission || null,
                          fuel || null,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </p>
                      <div className="mt-3 flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <span className="block truncate text-[12px] text-muted">{city}</span>
                          {publishedAgoLabel(listing.published_at) && (
                            <span className="mt-0.5 block truncate text-[11px] text-muted/80">
                              {publishedAgoLabel(listing.published_at)}
                            </span>
                          )}
                        </div>
                        {(listing.alternate_sources?.length ?? 0) > 0 ? (
                          <SourceLinks listing={listing} iconOnly className="shrink-0" />
                        ) : (
                          <SourceBadge source={listing.source} className="shrink-0 px-2 py-0.5" />
                        )}
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>

            {showControls && (
              <div className={cn("mt-4 flex items-center justify-between gap-4", controlsPad)}>
                <div className="flex flex-wrap items-center gap-1.5">
                  {listings.map((listing, index) => (
                    <button
                      key={listing.id}
                      type="button"
                      aria-label={`Перейти до оголошення ${index + 1}`}
                      aria-current={activeIndex === index ? "true" : undefined}
                      onClick={() => scrollToIndex(index)}
                      className={cn(
                        "h-2 rounded-full transition-all duration-300",
                        activeIndex === index ? "w-5 bg-emerald" : "w-2 bg-border hover:bg-muted/60",
                      )}
                    />
                  ))}
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    aria-label="Попереднє оголошення"
                    disabled={!canPrev}
                    onClick={() => scrollToIndex(activeIndex - 1)}
                    className={cn(
                      "flex h-9 w-9 items-center justify-center rounded-full border transition-all duration-200",
                      canPrev
                        ? "border-border text-ink hover:border-emerald hover:bg-emerald/5 hover:text-emerald"
                        : "cursor-not-allowed border-border/60 text-muted/40",
                    )}
                  >
                    <IconArrowLeft size={16} />
                  </button>
                  <button
                    type="button"
                    aria-label="Наступне оголошення"
                    disabled={!canNext}
                    onClick={() => scrollToIndex(activeIndex + 1)}
                    className={cn(
                      "flex h-9 w-9 items-center justify-center rounded-full border transition-all duration-200",
                      canNext
                        ? "border-border text-ink hover:border-emerald hover:bg-emerald/5 hover:text-emerald"
                        : "cursor-not-allowed border-border/60 text-muted/40",
                    )}
                  >
                    <IconArrowRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </section>

      <ListingDetailModal
        listing={selectedListing}
        onClose={() => {
          clearError();
          setSelectedListing(null);
        }}
        isFavorite={selectedListing ? favoriteIds.has(selectedListing.id) : false}
        favoriteLoading={selectedListing ? loadingIds.has(selectedListing.id) : false}
        onToggleFavorite={
          selectedListing && canFavorite ? () => toggleFavorite(selectedListing) : undefined
        }
        favoriteError={favoriteError}
      />
    </>
  );
}
