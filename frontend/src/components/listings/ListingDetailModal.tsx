"use client";

import Image from "next/image";
import { useCallback, useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { IconHeart, IconX, IconArrowLeft, IconArrowRight } from "@/components/icons";
import { ListingCompareButton } from "@/components/listings/ListingCompareButton";
import { ListingShareButton } from "@/components/listings/ListingShareButton";
import { ListingPhoto } from "@/components/listings/ListingPhoto";
import { ListingPlateBadge } from "@/components/listings/ListingPlateBadge";
import { AccidentBadge } from "@/components/listings/AccidentBadge";
import { UsaImportBadge } from "@/components/listings/UsaImportBadge";
import { useListingCompare } from "@/hooks/useListingCompare";
import { AutoRiaListingDetails } from "@/components/listings/AutoRiaListingDetails";
import { SellerContactBlock } from "@/components/listings/SellerContactBlock";
import {
  ListingOpenCta,
  keepListingMirrors,
  listingSourceLinks,
} from "@/components/listings/SourceLinks";
import { PublishedTimeBadge } from "@/components/listings/PublishedTimeBadge";
import { VinCheckButton } from "@/components/listings/VinCheckButton";
import { useAuth } from "@/contexts/AuthProvider";
import { getAutoRiaHighlights } from "@/lib/auto-ria-details";
import {
  listingAttributionUrl,
  listingIsNewCar,
  listingSourceSiteName,
} from "@/lib/listing-source";
import { openExternalUrl } from "@/lib/open-external";
import {
  ensurePhotosDeduped,
  noteTelegramPhotosState,
  telegramPhotosUnavailable,
} from "@/lib/telegram-photos";
import {
  ensureListingGallery,
  listingShouldFetchGallery,
} from "@/lib/listing-gallery";
import {
  ensureReonoPhotosDeduped,
  listingShouldFetchReonoGallery,
} from "@/lib/reono-photos";
import { hasVinCheck } from "@/lib/vin-check";
import { hasSellerContact } from "@/lib/seller-contact";
import { lockBodyScroll, unlockBodyScroll } from "@/lib/scroll-lock";
import {
  formatEngineVolume,
  resolveListingEngineVolume,
  resolveListingMileage,
} from "@/lib/listing-specs";
import { cn, formatMileage, publishedAgoLabel } from "@/lib/utils";
import { ListingPriceDisplay } from "@/components/listings/ListingPriceDisplay";
import { resolveDisplayCurrency, type DisplayCurrency } from "@/lib/display-currency";
import { resolveListingAccidentHad } from "@/lib/listing-accident";
import { resolveListingUsaImport } from "@/lib/listing-usa-import";
import { resolveListingImages } from "@/lib/listing-image-url";
import { listings as listingsApi } from "@/lib/api";
import type { Listing } from "@/types/api";

type Props = {
  listing: Listing | null;
  onClose: () => void;
  isFavorite?: boolean;
  favoriteLoading?: boolean;
  onToggleFavorite?: () => void;
  favoriteError?: string | null;
  /** Якщо не передано — валюта з профілю користувача. */
  displayCurrency?: DisplayCurrency;
  onListingUpdate?: (listing: Listing) => void;
};

const MODAL_ACTION_CLASS =
  "flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-ink transition-colors hover:bg-surface active:bg-surface";

export function ListingDetailModal({
  listing: listingProp,
  onClose,
  isFavorite = false,
  favoriteLoading = false,
  onToggleFavorite,
  favoriteError,
  displayCurrency: displayCurrencyProp,
  onListingUpdate,
}: Props) {
  const { user } = useAuth();
  const displayCurrency = resolveDisplayCurrency(
    displayCurrencyProp ?? user?.preferred_currency,
  );
  const [liveListing, setLiveListing] = useState<Listing | null>(listingProp);
  const [photosLoading, setPhotosLoading] = useState(false);
  const [photoIndex, setPhotoIndex] = useState(0);
  const galleryRef = useRef<HTMLDivElement>(null);
  const photoIndexRef = useRef(photoIndex);
  const dragStartY = useRef<number | null>(null);
  photoIndexRef.current = photoIndex;

  const listing = liveListing ?? listingProp;
  const isNewCar = listing ? listingIsNewCar(listing) : false;
  const { compareIds, toggle: toggleCompare, isFull } = useListingCompare();

  useEffect(() => {
    setLiveListing(listingProp);
    setPhotoIndex(0);
  }, [listingProp?.id]);

  useEffect(() => {
    if (!listingProp) return;
    const needsPhotos =
      listingShouldFetchGallery(listingProp) ||
      (listingProp.source === "telegram" &&
        (!listingProp.images || listingProp.images.length === 0));

    if (
      !needsPhotos ||
      (listingProp.source === "telegram" && telegramPhotosUnavailable())
    ) {
      setPhotosLoading(false);
      return;
    }

    let cancelled = false;
    let attempts = 0;
    let timer: number | undefined;
    setPhotosLoading(true);

    const poll = async () => {
      try {
        if (listingShouldFetchReonoGallery(listingProp)) {
          const reonoImages = await ensureReonoPhotosDeduped(listingProp);
          if (cancelled) return;
          if (reonoImages.length) {
            const merged = keepListingMirrors(
              { ...listingProp, images: reonoImages },
              listingProp,
            );
            setLiveListing(merged);
            onListingUpdate?.(merged);
          }
          setPhotosLoading(false);
          return;
        }

        if (listingShouldFetchGallery(listingProp)) {
          const enriched = await ensureListingGallery(listingProp);
          if (cancelled) return;
          if (enriched.images?.length) {
            const merged = keepListingMirrors(enriched, listingProp);
            setLiveListing(merged);
            onListingUpdate?.(merged);
          }
          setPhotosLoading(false);
          return;
        }

        const useEnsure = attempts === 0 || attempts % 3 === 0;
        const fresh = useEnsure
          ? await ensurePhotosDeduped(listingProp.id)
          : await listingsApi.get(listingProp.id);

        if (cancelled) return;
        noteTelegramPhotosState(fresh);

        const nextImages = resolveListingImages(fresh.images);
        if (nextImages.length) {
          const merged = keepListingMirrors(
            { ...fresh, images: nextImages },
            listingProp,
          );
          setLiveListing(merged);
          onListingUpdate?.(merged);
          setPhotosLoading(false);
          return;
        }

        if (fresh.source_data?.photos_unavailable) {
          setPhotosLoading(false);
          return;
        }

        const stillPending = Boolean(fresh.source_data?.photos_pending);
        if (!stillPending && attempts >= 2) {
          setPhotosLoading(false);
          return;
        }
      } catch {
        /* worker може ще не підхопити */
      }
      attempts += 1;
      if (!cancelled && attempts < 18) {
        timer = window.setTimeout(poll, attempts < 4 ? 800 : 2000);
      } else if (!cancelled) {
        setPhotosLoading(false);
      }
    };

    void poll();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [listingProp?.id, listingProp?.source, listingProp?.url, listingProp?.images?.length, onListingUpdate]);

  const scrollToPhoto = useCallback((index: number) => {
    setPhotoIndex(index);
    const container = galleryRef.current;
    if (!container) return;

    const slide = container.children[index] as HTMLElement | undefined;
    if (!slide) return;

    container.scrollTo({ left: slide.offsetLeft, behavior: "smooth" });
  }, []);

  const handleDragStart = useCallback((clientY: number) => {
    dragStartY.current = clientY;
  }, []);

  const handleDragEnd = useCallback(
    (clientY: number) => {
      if (dragStartY.current === null) return;
      const delta = clientY - dragStartY.current;
      dragStartY.current = null;
      if (delta > 48) onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (!listing) return;
    lockBodyScroll();
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      const count = listing.images.length;
      if (count <= 1) return;
      if (e.key === "ArrowLeft") {
        scrollToPhoto((photoIndexRef.current - 1 + count) % count);
      }
      if (e.key === "ArrowRight") {
        scrollToPhoto((photoIndexRef.current + 1) % count);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      unlockBodyScroll();
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [listing, onClose, scrollToPhoto]);

  useEffect(() => {
    const container = galleryRef.current;
    if (!container || !listing || listing.images.length <= 1) return;

    const slides = Array.from(container.children) as HTMLElement[];
    const observer = new IntersectionObserver(
      entries => {
        const visible = entries
          .filter(entry => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

        if (!visible.length) return;

        const index = slides.indexOf(visible[0].target as HTMLElement);
        if (index >= 0) setPhotoIndex(index);
      },
      { root: container, threshold: 0.6 },
    );

    slides.forEach(slide => observer.observe(slide));
    return () => observer.disconnect();
  }, [listing]);

  useEffect(() => {
    if (!listing) return;
    galleryRef.current?.scrollTo({ left: 0 });
  }, [listing?.id]);

  if (!listing) return null;

  const photos = resolveListingImages(listing.images);
  const hasAutoRiaDetails =
    listing.source === "auto_ria" &&
    listing.source_data &&
    Object.keys(listing.source_data).length > 0;
  const descriptionText = (() => {
    const fromListing = (listing.description || "").trim();
    if (fromListing) return fromListing;
    const fromSource = listing.source_data?.description;
    return typeof fromSource === "string" ? fromSource.trim() : "";
  })();

  const highlights = hasAutoRiaDetails ? [] : getAutoRiaHighlights(listing.source_data);
  const mileageKm = resolveListingMileage(listing);
  const engineVolume = resolveListingEngineVolume(listing);
  const plateLabel = listing.plate?.trim() || "";
  const hadAccident = resolveListingAccidentHad(listing) === true;
  const isUsaImport = resolveListingUsaImport(listing);
  const source = listing.source_data ?? {};
  const priceUsd = typeof source.USD === "number" ? source.USD : null;
  const priceEur = typeof source.EUR === "number" ? source.EUR : null;

  const specs = hasAutoRiaDetails
    ? []
    : [
        { label: "Рік", value: listing.year ? String(listing.year) : "—" },
        { label: "Пробіг", value: mileageKm != null && mileageKm > 0 ? formatMileage(mileageKm) : "—" },
        {
          label: "Обʼєм двигуна",
          value: engineVolume != null ? formatEngineVolume(engineVolume) : "—",
        },
        { label: "Паливо", value: listing.fuel || "—" },
        { label: "КПП", value: listing.transmission || "—" },
        { label: "Регіон", value: listing.region || "—" },
        {
          label: "Продавець",
          value: listing.seller_type === "dealer" ? "Автосалон" : "Приват",
        },
        ...(listing.vin ? [{ label: "VIN", value: listing.vin }] : []),
        ...(priceUsd ? [{ label: "Ціна USD", value: priceUsd.toLocaleString("uk-UA") }] : []),
        ...(priceEur ? [{ label: "Ціна EUR", value: priceEur.toLocaleString("uk-UA") }] : []),
      ];

  return (
    <div
      className="fixed inset-0 z-[120] flex items-end justify-center p-0 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="listing-modal-title"
    >
      <button
        type="button"
        aria-label="Закрити"
        className="absolute inset-0 bg-ink/60"
        onClick={onClose}
      />

      <div className="relative z-10 flex max-h-[92dvh] w-full max-w-[880px] flex-col overflow-hidden rounded-t-[1.5rem] border border-border bg-white shadow-[0_24px_80px_-20px_rgba(10,12,14,0.35)] sm:rounded-[1.5rem]">
        <div className="z-30 shrink-0 border-b border-border/60 bg-white/95 backdrop-blur-md">
          <button
            type="button"
            aria-label="Згорнути"
            onClick={onClose}
            onTouchStart={e => handleDragStart(e.touches[0].clientY)}
            onTouchEnd={e => handleDragEnd(e.changedTouches[0].clientY)}
            onPointerDown={e => {
              if (e.pointerType === "mouse") handleDragStart(e.clientY);
            }}
            onPointerUp={e => {
              if (e.pointerType === "mouse") handleDragEnd(e.clientY);
            }}
            className="flex w-full touch-none justify-center px-4 pb-1 pt-2.5 sm:hidden"
          >
            <span className="h-1 w-10 rounded-full bg-border" />
          </button>

          <div className="flex items-center gap-3 px-3 pb-2.5 sm:px-4 sm:pb-3">
            <div className="min-w-0 flex-1 sm:hidden">
              <h2 className="truncate text-[15px] font-bold leading-snug text-ink">
                {isNewCar && <strong className="text-blue-600">НОВИЙ </strong>}
                {listing.title}
              </h2>
            </div>
            <div className="hidden min-w-0 flex-1 sm:block">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">Деталі авто</p>
              <p className="truncate text-[15px] font-bold leading-snug text-ink">
                {isNewCar && <strong className="text-blue-600">НОВИЙ </strong>}
                {listing.title}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              {listing && (
                <ListingShareButton
                  listing={listing}
                  variant="default"
                  size="md"
                  className={MODAL_ACTION_CLASS}
                />
              )}
              {listing && (
                <ListingCompareButton
                  active={compareIds.has(listing.id)}
                  disabled={isFull && !compareIds.has(listing.id)}
                  onToggle={() => toggleCompare(listing)}
                  variant="default"
                  size="md"
                  className={MODAL_ACTION_CLASS}
                />
              )}
              {onToggleFavorite && (
                <button
                  type="button"
                  aria-label={isFavorite ? "Прибрати з обраного" : "Додати в обране"}
                  aria-pressed={isFavorite}
                  disabled={favoriteLoading}
                  onClick={onToggleFavorite}
                  className={cn(
                    MODAL_ACTION_CLASS,
                    isFavorite ? "text-emerald" : "text-muted hover:text-emerald-dark",
                    favoriteLoading && "opacity-60",
                  )}
                >
                  <IconHeart size={18} className={cn(isFavorite && "fill-current")} />
                </button>
              )}
              <button type="button" aria-label="Закрити" onClick={onClose} className={MODAL_ACTION_CLASS}>
                <IconX size={18} />
              </button>
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
          {/* Mobile gallery */}
          <div className="relative aspect-[16/10] w-full bg-surface sm:hidden">
            {photos.length > 0 ? (
              <div
                ref={galleryRef}
                className="flex h-full w-full snap-x snap-mandatory overflow-x-auto scroll-smooth scrollbar-hide touch-pan-x"
              >
                {photos.map((src, index) => (
                  <div
                    key={`${src}-${index}`}
                    className="relative h-full w-full shrink-0 snap-start snap-always"
                  >
                    <ListingPhoto
                      src={src}
                      alt={`${listing.title} — фото ${index + 1}`}
                      sizes="100vw"
                      priority={index === 0}
                      logoClassName="h-12"
                    />
                  </div>
                ))}
              </div>
            ) : (
              <ListingPhoto
                src={null}
                alt={listing.title}
                pending={photosLoading}
                pendingLabel="Підвантажуємо фото…"
                className="h-full"
                logoClassName="h-12"
              />
            )}

            {photos.length > 1 && (
              <>
                <button
                  type="button"
                  aria-label="Попереднє фото"
                  onClick={() =>
                    scrollToPhoto((photoIndex - 1 + photos.length) % photos.length)
                  }
                  className={cn(
                    "absolute left-2 top-1/2 z-[1] flex h-9 w-9 -translate-y-1/2 items-center justify-center",
                    "rounded-full bg-ink/70 text-white shadow-sm backdrop-blur-sm",
                    "active:bg-ink/85 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70",
                  )}
                >
                  <IconArrowLeft size={16} />
                </button>
                <button
                  type="button"
                  aria-label="Наступне фото"
                  onClick={() => scrollToPhoto((photoIndex + 1) % photos.length)}
                  className={cn(
                    "absolute right-2 top-1/2 z-[1] flex h-9 w-9 -translate-y-1/2 items-center justify-center",
                    "rounded-full bg-ink/70 text-white shadow-sm backdrop-blur-sm",
                    "active:bg-ink/85 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70",
                  )}
                >
                  <IconArrowRight size={16} />
                </button>
                <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-black/50 px-2.5 py-1 text-[11px] font-semibold tabular-nums text-white backdrop-blur-sm">
                  {photoIndex + 1} / {photos.length}
                </div>
              </>
            )}
            <div className="pointer-events-none absolute bottom-3 left-3">
              <PublishedTimeBadge date={listing.published_at} short />
            </div>
            {plateLabel ? (
              <div className="pointer-events-none absolute bottom-3 left-1/2 z-[1] -translate-x-1/2">
                <ListingPlateBadge plate={plateLabel} size="md" elevated />
              </div>
            ) : null}
          </div>

          {photos.length > 1 && (
            <div className="flex gap-2 overflow-x-auto border-b border-border px-4 py-3 scrollbar-hide sm:hidden">
              {photos.map((src, index) => (
                <button
                  key={`${src}-${index}-thumb-mobile`}
                  type="button"
                  onClick={() => scrollToPhoto(index)}
                  className={cn(
                    "relative h-14 w-20 shrink-0 overflow-hidden rounded-lg border-2 transition-colors",
                    index === photoIndex ? "border-emerald" : "border-transparent opacity-70 hover:opacity-100",
                  )}
                >
                  <Image src={src} alt="" fill className="object-cover" sizes="80px" unoptimized />
                </button>
              ))}
            </div>
          )}

          {/* Desktop: photo left, summary right */}
          <div className="hidden border-b border-border/60 sm:block">
            <div className="flex gap-5 p-5">
              <div className="w-1/2 min-w-0">
                <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-surface">
                  {photos.length > 0 ? (
                    <ListingPhoto
                      src={photos[photoIndex] ?? photos[0]}
                      alt={listing.title}
                      sizes="50vw"
                      priority
                      logoClassName="h-14"
                    />
                  ) : (
                    <ListingPhoto
                      src={null}
                      alt={listing.title}
                      pending={photosLoading}
                      pendingLabel="Підвантажуємо фото…"
                      className="h-full"
                      logoClassName="h-14"
                    />
                  )}
                  {photos.length > 1 && (
                    <>
                      <button
                        type="button"
                        aria-label="Попереднє фото"
                        onClick={() => setPhotoIndex(i => (i - 1 + photos.length) % photos.length)}
                        className={cn(
                          "absolute left-2 top-1/2 z-[1] flex h-9 w-9 -translate-y-1/2 items-center justify-center",
                          "rounded-full bg-ink/70 text-white shadow-sm backdrop-blur-sm transition-colors",
                          "hover:bg-ink/85 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70",
                        )}
                      >
                        <IconArrowLeft size={16} />
                      </button>
                      <button
                        type="button"
                        aria-label="Наступне фото"
                        onClick={() => setPhotoIndex(i => (i + 1) % photos.length)}
                        className={cn(
                          "absolute right-2 top-1/2 z-[1] flex h-9 w-9 -translate-y-1/2 items-center justify-center",
                          "rounded-full bg-ink/70 text-white shadow-sm backdrop-blur-sm transition-colors",
                          "hover:bg-ink/85 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70",
                        )}
                      >
                        <IconArrowRight size={16} />
                      </button>
                      <div className="absolute bottom-2 right-2 rounded-full bg-black/55 px-2 py-0.5 text-[10px] font-semibold tabular-nums text-white">
                        {photoIndex + 1} / {photos.length}
                      </div>
                    </>
                  )}
                  <div className="absolute bottom-2 left-2">
                    <PublishedTimeBadge date={listing.published_at} short />
                  </div>
                  {plateLabel ? (
                    <div className="pointer-events-none absolute bottom-2 left-1/2 z-[1] -translate-x-1/2">
                      <ListingPlateBadge plate={plateLabel} size="md" elevated />
                    </div>
                  ) : null}
                </div>

                {photos.length > 1 && (
                  <div className="mt-2.5 flex gap-1.5 overflow-x-auto scrollbar-hide">
                    {photos.map((src, index) => (
                      <button
                        key={`${src}-${index}-thumb-desktop`}
                        type="button"
                        onClick={() => setPhotoIndex(index)}
                        className={cn(
                          "relative h-12 w-16 shrink-0 overflow-hidden rounded-lg border-2 transition-colors",
                          index === photoIndex
                            ? "border-emerald"
                            : "border-transparent opacity-70 hover:opacity-100",
                        )}
                      >
                        <Image src={src} alt="" fill className="object-cover" sizes="64px" unoptimized />
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="w-1/2 min-w-0">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <h2 id="listing-modal-title" className="text-[20px] font-bold leading-snug text-ink">
                      {isNewCar && <strong className="text-blue-600">НОВИЙ </strong>}
                      {listing.title}
                    </h2>
                    {(hadAccident || isUsaImport) && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {hadAccident && <AccidentBadge variant="label" />}
                        {isUsaImport && <UsaImportBadge variant="label" />}
                      </div>
                    )}
                    <p className="mt-1 text-[13px] text-muted">
                      {listing.brand} {listing.model}
                    </p>
                    {plateLabel ? (
                      <div className="mt-3">
                        <ListingPlateBadge plate={plateLabel} size="md" />
                      </div>
                    ) : null}
                    {publishedAgoLabel(listing.published_at) && (
                      <p className="mt-1 text-[12px] text-muted/80">
                        {publishedAgoLabel(listing.published_at)}
                      </p>
                    )}
                  </div>
                  <div className="shrink-0 text-right">
                    {listing && (
                      <ListingPriceDisplay
                        listing={listing}
                        displayCurrency={displayCurrency}
                        priceClassName="text-[26px]"
                        className="items-end"
                      />
                    )}
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-1.5">
                  {listing.year > 0 && (
                    <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
                      {listing.year}
                    </span>
                  )}
                  {mileageKm != null && mileageKm > 0 && (
                    <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
                      {formatMileage(mileageKm)}
                    </span>
                  )}
                  {engineVolume != null && (
                    <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
                      {formatEngineVolume(engineVolume)}
                    </span>
                  )}
                  {listing.transmission && (
                    <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
                      {listing.transmission}
                    </span>
                  )}
                  {listing.fuel && (
                    <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
                      {listing.fuel.split(",")[0]?.trim()}
                    </span>
                  )}
                  {listing.region && (
                    <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
                      {listing.region.split(",")[0]?.trim()}
                    </span>
                  )}
                  <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
                    {listing.seller_type === "dealer" ? "Автосалон" : "Приват"}
                  </span>
                </div>

                {highlights.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {highlights.map((item, index) => (
                      <span
                        key={`${item}-${index}`}
                        className="rounded-full bg-emerald-light/50 px-2.5 py-1 text-[11px] font-medium text-emerald-dark"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-5 px-4 py-5 sm:px-6 sm:py-6">
            {/* Mobile-only price block (desktop shows it in top row) */}
            <div className="flex flex-wrap items-end justify-between gap-3 sm:hidden">
              <div>
                {(hadAccident || isUsaImport) && (
                  <div className="mb-3 flex flex-wrap gap-2">
                    {hadAccident && <AccidentBadge variant="label" />}
                    {isUsaImport && <UsaImportBadge variant="label" />}
                  </div>
                )}
                {plateLabel ? (
                  <div className="mb-3">
                    <ListingPlateBadge plate={plateLabel} size="md" />
                  </div>
                ) : null}
                {listing && (
                  <ListingPriceDisplay
                    listing={listing}
                    displayCurrency={displayCurrency}
                    priceClassName="text-[28px]"
                  />
                )}
                <p className="mt-1.5 text-[12px] text-muted">
                  {listing.brand} {listing.model}
                </p>
                {publishedAgoLabel(listing.published_at) && (
                  <p className="mt-1 text-[12px] text-muted/80">
                    {publishedAgoLabel(listing.published_at)}
                  </p>
                )}
              </div>
            </div>

            {descriptionText && (
              <div>
                <h3 className="text-[13px] font-bold text-ink">Опис</h3>
                <p className="mt-2 text-[13px] leading-relaxed text-muted whitespace-pre-wrap">
                  {descriptionText}
                </p>
              </div>
            )}

            {specs.length > 0 && (
              <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
                {specs.map(({ label, value }) => (
                  <div key={label} className="rounded-xl border border-border/70 bg-surface/60 px-3 py-2.5">
                    <div className="text-[10px] font-semibold uppercase tracking-wide text-muted">{label}</div>
                    <div className="mt-1 break-all text-[13px] font-semibold text-ink">{value}</div>
                  </div>
                ))}
              </div>
            )}

            {hasSellerContact(listing) && <SellerContactBlock listing={listing} compact />}

            {highlights.length > 0 && (
              <div className="flex flex-wrap gap-1.5 sm:hidden">
                {highlights.map((item, index) => (
                  <span
                    key={`${item}-${index}`}
                    className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-ink"
                  >
                    {item}
                  </span>
                ))}
              </div>
            )}

            {hasAutoRiaDetails && (
              <AutoRiaListingDetails listing={listing} omitDescription={Boolean(descriptionText)} />
            )}
            {listing.vin_checked && listing.source === "auto_ria" && (
              <p className="text-center text-[12px] font-medium text-emerald-dark">
                VIN-код перевірено на AUTO.RIA
              </p>
            )}

            <p className="pb-2 text-center text-[11px] text-muted">
              Дані надано{" "}
              {listingSourceLinks(listing).map((link, index, arr) => (
                <span key={`${link.source}-${link.url}`}>
                  {index > 0 ? (index === arr.length - 1 ? " та " : ", ") : null}
                  <a
                    href={listingAttributionUrl(link.source, link.url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={e => openExternalUrl(listingAttributionUrl(link.source, link.url), e)}
                    className="text-emerald-dark hover:underline"
                  >
                    {listingSourceSiteName(link.source)}
                  </a>
                </span>
              ))}
            </p>
          </div>
        </div>

        <div className="shrink-0 border-t border-border bg-white px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-6">
          {favoriteError && (
            <p role="alert" className="mb-2 text-center text-[12px] font-medium text-red-600">
              {favoriteError}
            </p>
          )}

          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <ListingOpenCta listing={listing} className="flex-1 sm:min-w-[240px]" />
            {hasVinCheck(listing) && (
              <VinCheckButton
                listing={listing}
                size="md"
                showSummary
                className="w-full sm:w-auto sm:min-w-[180px]"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
