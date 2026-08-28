"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { IconArrowLeft, IconArrowRight, IconEye } from "@/components/icons";
import { ListingFavoriteButton } from "@/components/listings/ListingFavoriteButton";
import { ListingCompareButton } from "@/components/listings/ListingCompareButton";
import { ListingShareButton } from "@/components/listings/ListingShareButton";
import { VinCheckButton } from "@/components/listings/VinCheckButton";
import { ListingPhoto } from "@/components/listings/ListingPhoto";
import { ListingPriceDisplay } from "@/components/listings/ListingPriceDisplay";
import { getAutoRiaHighlights } from "@/lib/auto-ria-details";
import {
  formatEngineVolume,
  resolveListingEngineVolume,
  resolveListingMileage,
} from "@/lib/listing-specs";
import { SourceBadge } from "@/components/listings/SourceBadge";
import { SourceLinks } from "@/components/listings/SourceLinks";
import { PublishedTimeBadge } from "@/components/listings/PublishedTimeBadge";
import { listingIsNewCar } from "@/lib/listing-source";
import { useListingVinCheck } from "@/hooks/useVinCheckCache";
import { useListingPhotoHydration } from "@/hooks/useListingPhotoHydration";
import { useListingViewed } from "@/hooks/useListingViewed";
import { hasVinCheck, resolveListingVin } from "@/lib/vin-check";
import { cn, formatMileage, publishedAgoLabel, refreshedAgoLabel } from "@/lib/utils";
import { resolveDisplayCurrency, type DisplayCurrency } from "@/lib/display-currency";
import { useAuth } from "@/contexts/AuthProvider";
import type { Listing } from "@/types/api";

type Props = {
  listing: Listing;
  onClick: () => void;
  className?: string;
  isFavorite?: boolean;
  favoriteLoading?: boolean;
  onToggleFavorite?: () => void;
  isCompared?: boolean;
  compareDisabled?: boolean;
  onToggleCompare?: () => void;
  /** Валюта відображення ($ за замовчуванням). */
  displayCurrency?: DisplayCurrency;
  /** Приховати бейджі зниження (напр. у сповіщеннях — вже є банер зверху). */
  hidePriceDrop?: boolean;
};

function shortRegion(region: string) {
  const city = region.split(",")[0]?.trim();
  return city || region;
}

export function ListingCard({
  listing,
  onClick,
  className,
  isFavorite = false,
  favoriteLoading = false,
  onToggleFavorite,
  isCompared = false,
  compareDisabled = false,
  onToggleCompare,
  displayCurrency: displayCurrencyProp,
  hidePriceDrop = false,
}: Props) {
  const { user } = useAuth();
  const displayCurrency = resolveDisplayCurrency(
    displayCurrencyProp ?? user?.preferred_currency,
  );
  const { images, rootRef, photosPending } = useListingPhotoHydration(listing);
  const isViewed = useListingViewed(listing.id);
  const fuel = typeof listing.fuel === "string" ? listing.fuel : "";
  const region = typeof listing.region === "string" ? listing.region : "";
  const sellerLabel = listing.seller_type === "dealer" ? "Автосалон" : "Приват";
  const resolvedVin = resolveListingVin(listing);
  const cachedVinCheck = useListingVinCheck(listing);
  const showVinBlock = Boolean(resolvedVin) || hasVinCheck(listing);
  const highlights = getAutoRiaHighlights(listing.source_data).slice(0, 3);
  const mileageKm = resolveListingMileage(listing);
  const engineVolume = resolveListingEngineVolume(listing);
  const publishedLabel = publishedAgoLabel(listing.published_at);
  const refreshedLabel =
    listing.refreshed_at && listing.refreshed_at !== listing.published_at
      ? refreshedAgoLabel(listing.refreshed_at)
      : "";
  // На фото — дата публікації, не lastRefresh (підняття на OLX).
  const timeBadgeDate = listing.published_at;
  const hasMirrorSources = (listing.alternate_sources?.length ?? 0) > 0;
  const isNewForMonitor = Boolean(listing.is_new);
  const isNewCar = listingIsNewCar(listing);
  const [photoIndex, setPhotoIndex] = useState(0);
  const photoCount = images.length;
  const safeIndex = photoCount > 0 ? ((photoIndex % photoCount) + photoCount) % photoCount : 0;
  const currentPhoto = photoCount > 0 ? images[safeIndex] : null;
  const showGalleryNav = photoCount > 1;

  const goPhoto = (delta: number) => (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setPhotoIndex(prev => {
      const next = prev + delta;
      if (next < 0) return photoCount - 1;
      if (next >= photoCount) return 0;
      return next;
    });
  };

  useEffect(() => {
    setPhotoIndex(0);
  }, [listing.id, photoCount]);

  const handlePhotoAreaEnter = () => {
    if (photoCount <= 1) return;
    setPhotoIndex(prev => (prev + 1) % photoCount);
  };

  const handlePhotoAreaLeave = () => {
    setPhotoIndex(0);
  };

  return (
    <article
      ref={rootRef as React.RefObject<HTMLElement>}
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={e => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      className={cn(
        "group cursor-pointer overflow-hidden rounded-2xl border border-border/80 bg-white text-left shadow-[0_2px_12px_-6px_rgba(10,12,14,0.12)] transition-all",
        "hover:border-emerald/30 hover:shadow-[0_8px_24px_-10px_rgba(10,12,14,0.16)]",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald/40",
        "sm:flex sm:gap-5 sm:p-5 lg:gap-6 lg:p-6 lg:rounded-[1.35rem]",
        isNewForMonitor && "border-emerald/40 ring-1 ring-emerald/20",
        isViewed && "border-border/70 bg-surface/40 opacity-[0.92]",
        className,
      )}
      onMouseEnter={handlePhotoAreaEnter}
      onMouseLeave={handlePhotoAreaLeave}
    >
      {/* Mobile: full-width photo on top */}
      <div className="relative aspect-[16/10] w-full bg-surface sm:hidden">
        <ListingPhoto
          src={currentPhoto}
          alt={listing.title}
          pending={photosPending && !currentPhoto}
          sizes="100vw"
          pendingLabel="Завантаження фото…"
        />
        <div className="absolute inset-x-0 top-0 z-[1] flex items-start justify-between gap-2 p-3">
          <div className="flex flex-wrap items-center gap-1.5">
            {isNewForMonitor && (
              <span className="rounded-full bg-emerald px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-white shadow-sm">
                Нове
              </span>
            )}
            {isNewCar && (
              <span className="rounded-full bg-blue-600 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-white shadow-sm">
                Новий
              </span>
            )}
            {isViewed && (
              <span className="inline-flex items-center gap-1 rounded-full bg-ink/70 px-2.5 py-1 text-[10px] font-semibold text-white shadow-sm backdrop-blur-sm">
                <IconEye size={11} />
                Переглянуто
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <ListingShareButton listing={listing} variant="overlay" />
            {onToggleCompare && (
              <ListingCompareButton
                active={isCompared}
                disabled={compareDisabled}
                onToggle={onToggleCompare}
                variant="overlay"
              />
            )}
            {onToggleFavorite && (
              <ListingFavoriteButton
                active={isFavorite}
                loading={favoriteLoading}
                onToggle={onToggleFavorite}
                variant="overlay"
              />
            )}
            <span className="rounded-full bg-ink/75 px-2.5 py-1 text-[10px] font-medium text-white">
              {sellerLabel}
            </span>
          </div>
        </div>
        {showGalleryNav && (
          <>
            <button
              type="button"
              aria-label="Попереднє фото"
              onClick={goPhoto(-1)}
              className={cn(
                "absolute left-2 top-1/2 z-[1] flex h-9 w-9 -translate-y-1/2 items-center justify-center",
                "rounded-full bg-ink/70 text-white shadow-sm backdrop-blur-sm",
                "active:bg-ink/85 focus:outline-none",
              )}
            >
              <IconArrowLeft size={16} />
            </button>
            <button
              type="button"
              aria-label="Наступне фото"
              onClick={goPhoto(1)}
              className={cn(
                "absolute right-2 top-1/2 z-[1] flex h-9 w-9 -translate-y-1/2 items-center justify-center",
                "rounded-full bg-ink/70 text-white shadow-sm backdrop-blur-sm",
                "active:bg-ink/85 focus:outline-none",
              )}
            >
              <IconArrowRight size={16} />
            </button>
            <span className="absolute bottom-2 right-2 z-[1] rounded-full bg-ink/70 px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-white backdrop-blur-sm">
              {safeIndex + 1}/{photoCount}
            </span>
          </>
        )}
        <div className="absolute bottom-2 left-2 z-[1]">
          <PublishedTimeBadge date={timeBadgeDate} short />
        </div>
      </div>

      {/* Desktop: thumbnail left with photo arrows */}
      <div className="relative hidden h-44 w-64 shrink-0 overflow-hidden rounded-xl bg-surface sm:block lg:h-56 lg:w-[22rem] lg:rounded-2xl">
        <ListingPhoto
          src={currentPhoto}
          alt={listing.title}
          pending={photosPending && !currentPhoto}
          sizes="(min-width: 1024px) 352px, 256px"
          imageClassName="transition-transform duration-300 group-hover:scale-[1.02]"
          pendingLabel="фото…"
          logoClassName="h-10 sm:h-11"
        />
        <div className="absolute right-2 top-2 z-[1] flex items-center gap-1.5">
          <ListingShareButton listing={listing} variant="overlay" />
          {onToggleCompare && (
            <ListingCompareButton
              active={isCompared}
              disabled={compareDisabled}
              onToggle={onToggleCompare}
              variant="overlay"
            />
          )}
          {onToggleFavorite && (
            <ListingFavoriteButton
              active={isFavorite}
              loading={favoriteLoading}
              onToggle={onToggleFavorite}
              variant="overlay"
            />
          )}
        </div>
        {showGalleryNav && (
          <>
            <button
              type="button"
              aria-label="Попереднє фото"
              onClick={goPhoto(-1)}
              className={cn(
                "absolute left-1.5 top-1/2 z-[1] flex h-8 w-8 -translate-y-1/2 items-center justify-center lg:h-9 lg:w-9",
                "rounded-full bg-ink/70 text-white opacity-0 shadow-sm backdrop-blur-sm transition-opacity",
                "hover:bg-ink/85 group-hover:opacity-100 focus:opacity-100 focus:outline-none",
              )}
            >
              <IconArrowLeft size={14} />
            </button>
            <button
              type="button"
              aria-label="Наступне фото"
              onClick={goPhoto(1)}
              className={cn(
                "absolute right-1.5 top-1/2 z-[1] flex h-8 w-8 -translate-y-1/2 items-center justify-center lg:h-9 lg:w-9",
                "rounded-full bg-ink/70 text-white opacity-0 shadow-sm backdrop-blur-sm transition-opacity",
                "hover:bg-ink/85 group-hover:opacity-100 focus:opacity-100 focus:outline-none",
              )}
            >
              <IconArrowRight size={14} />
            </button>
            <span className="absolute bottom-2 right-2 z-[1] rounded-full bg-ink/70 px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-white backdrop-blur-sm">
              {safeIndex + 1}/{photoCount}
            </span>
          </>
        )}
        <div className="absolute bottom-2 left-2 z-[1]">
          <PublishedTimeBadge date={timeBadgeDate} short />
        </div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col p-4 pt-3.5 sm:p-0 sm:justify-center">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              {isNewForMonitor && (
                <span className="hidden rounded-full bg-emerald px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white sm:inline-flex">
                  Нове
                </span>
              )}
            {isNewCar && (
              <span className="hidden rounded-full bg-blue-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white sm:inline-flex">
                Новий
              </span>
            )}
              {isViewed && (
                <span className="hidden items-center gap-1 rounded-full bg-surface px-2 py-0.5 text-[10px] font-semibold text-muted sm:inline-flex">
                  <IconEye size={11} />
                  Переглянуто
                </span>
              )}
              <h3 className="line-clamp-2 text-[16px] font-bold leading-snug text-ink sm:text-[16px] sm:line-clamp-2 lg:text-[18px]">
                {listing.title}
              </h3>
            </div>
            <div className="mt-2 sm:hidden">
              <ListingPriceDisplay
                listing={listing}
                displayCurrency={displayCurrency}
                priceClassName="text-[22px]"
                showBadge={!hidePriceDrop}
              />
            </div>
          </div>
          <div className="hidden shrink-0 text-right sm:block">
            <ListingPriceDisplay
              listing={listing}
              displayCurrency={displayCurrency}
              priceClassName="text-[22px] lg:text-[26px]"
              className="items-end"
              showBadge={!hidePriceDrop}
            />
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5 sm:mt-3 lg:mt-4 lg:gap-2">
          {listing.year > 0 && (
            <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink lg:px-3.5 lg:py-1.5 lg:text-[13px]">
              {listing.year}
            </span>
          )}
          {mileageKm != null && mileageKm > 0 && (
            <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink lg:px-3.5 lg:py-1.5 lg:text-[13px]">
              {formatMileage(mileageKm)}
            </span>
          )}
          {engineVolume != null && (
            <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink lg:px-3.5 lg:py-1.5 lg:text-[13px]">
              {formatEngineVolume(engineVolume)}
            </span>
          )}
          {listing.transmission && (
            <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink lg:px-3.5 lg:py-1.5 lg:text-[13px]">
              {listing.transmission}
            </span>
          )}
          {fuel && (
            <span className="max-w-full truncate rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink lg:px-3.5 lg:py-1.5 lg:text-[13px]">
              {fuel.split(",")[0]?.trim()}
            </span>
          )}
          {highlights.map((item, index) => (
            <span
              key={`${item}-${index}`}
              className="max-w-full truncate rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink lg:px-3.5 lg:py-1.5 lg:text-[13px]"
            >
              {item}
            </span>
          ))}
        </div>

        {showVinBlock && (
          <div
            className="mt-3 flex flex-col gap-2"
            onClick={e => e.stopPropagation()}
            onKeyDown={e => e.stopPropagation()}
          >
            <div className="flex flex-wrap items-center gap-2">
              {resolvedVin && (
                <span className="rounded-full bg-surface px-2.5 py-1 font-mono text-[11px] font-medium tracking-wide text-ink">
                  VIN: {resolvedVin}
                </span>
              )}
              {listing.vin_checked && !cachedVinCheck && (
                <Badge variant="emerald" className="text-[10px]">
                  VIN перевірено
                </Badge>
              )}
            </div>
            <VinCheckButton listing={listing} showSummary />
          </div>
        )}

        <div className="mt-3 flex items-center gap-2 border-t border-border/60 pt-3 sm:mt-auto sm:border-0 sm:pt-2.5">
          <div className="min-w-0 flex-1">
            <span className="block truncate text-[12px] text-muted">{shortRegion(region)}</span>
            {refreshedLabel ? (
              <span className="mt-0.5 block truncate text-[11px] text-muted/80">
                {refreshedLabel}
                {publishedLabel ? ` · ${publishedLabel}` : ""}
              </span>
            ) : (
              publishedLabel && (
                <span className="mt-0.5 block truncate text-[11px] text-muted/80">{publishedLabel}</span>
              )
            )}
          </div>
          <span className="flex items-center gap-1.5">
            {hasMirrorSources && (
              <span className="hidden rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 sm:inline-flex">
                VIN-дубль
              </span>
            )}
            {hasMirrorSources ? (
              <SourceLinks listing={listing} iconOnly />
            ) : (
              <SourceBadge source={listing.source} variant="outline" />
            )}
            <span className="hidden text-[11px] text-muted sm:inline">{sellerLabel}</span>
          </span>
          <span
            className={cn(
              "flex items-center gap-0.5 text-[12px] font-semibold sm:ml-auto",
              isViewed ? "text-muted" : "text-emerald-dark",
            )}
          >
            {isViewed ? (
              <>
                <IconEye size={12} />
                Переглянуто
              </>
            ) : (
              <>
                Деталі
                <IconArrowRight
                  size={12}
                  className="transition-transform group-hover:translate-x-0.5"
                />
              </>
            )}
          </span>
        </div>
      </div>
    </article>
  );
}
