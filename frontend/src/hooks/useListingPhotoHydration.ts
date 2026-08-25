"use client";

import { useEffect, useRef, useState } from "react";
import { listings as listingsApi } from "@/lib/api";
import { resolveListingImages } from "@/lib/listing-image-url";
import {
  ensurePhotosDeduped,
  noteTelegramPhotosState,
  telegramPhotosUnavailable,
} from "@/lib/telegram-photos";
import {
  ensureReonoPhotosDeduped,
  listingNeedsReonoPhotos,
} from "@/lib/reono-photos";
import type { Listing } from "@/types/api";

function listingNeedsPhotoHydration(listing: Listing): boolean {
  if (listingNeedsReonoPhotos(listing)) return true;
  if ((listing.source || "").toLowerCase() !== "telegram") return false;
  if (listing.images?.length) return false;
  return !telegramPhotosUnavailable();
}

/** Retry: швидко на старті, потім рідше (ensure-photos може чекати worker до ~30s). */
const RETRY_INTERVALS = [400, 800, 1500, 2500, 4000, 6000];
const MAX_ATTEMPTS = 18;

function retryDelayMs(attempt: number): number {
  return RETRY_INTERVALS[Math.min(attempt, RETRY_INTERVALS.length - 1)];
}

function applyImages(raw: string[] | null | undefined): string[] {
  return resolveListingImages(raw);
}

/** Підвантажує мінімум 1 фото для Telegram-карток у каталозі (лише видимі). */
export function useListingPhotoHydration(listing: Listing) {
  const rootRef = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);
  const [images, setImages] = useState<string[]>(applyImages(listing.images));
  const [photosPending, setPhotosPending] = useState(false);

  useEffect(() => {
    setImages(applyImages(listing.images));
  }, [listing.id]);

  useEffect(() => {
    if (listing.images?.length) {
      setImages(applyImages(listing.images));
      setPhotosPending(false);
    }
  }, [listing.id, listing.images]);

  useEffect(() => {
    const node = rootRef.current;
    if (!node || typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      entries => {
        if (entries.some(entry => entry.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "200px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [listing.id]);

  useEffect(() => {
    if (!visible || !listingNeedsPhotoHydration(listing)) return;

    let cancelled = false;
    let attempts = 0;
    let timer: number | undefined;

    setPhotosPending(true);

    const poll = async () => {
      try {
        if (listingNeedsReonoPhotos(listing)) {
          const reonoImages = await ensureReonoPhotosDeduped(listing);
          if (cancelled) return;
          if (reonoImages.length) {
            setImages(reonoImages);
          }
          setPhotosPending(false);
          return;
        }

        const useEnsure = attempts === 0 || attempts % 3 === 0;
        const fresh = useEnsure
          ? await ensurePhotosDeduped(listing.id)
          : await listingsApi.get(listing.id);

        if (cancelled) return;

        noteTelegramPhotosState(fresh);

        const nextImages = applyImages(fresh.images);
        if (nextImages.length) {
          setImages(nextImages);
          setPhotosPending(false);
          return;
        }

        // Бекенд знає, що завантажити нічим (сесія Telethon лежить) —
        // тримати спінер до кінця спроб немає сенсу.
        if (fresh.source_data?.photos_unavailable) {
          setPhotosPending(false);
          return;
        }

        const stillPending = Boolean(fresh.source_data?.photos_pending);
        if (!stillPending && attempts >= 2) {
          setPhotosPending(false);
          return;
        }
      } catch {
        /* worker / Telethon обробляє чергу */
      }

      attempts += 1;
      if (!cancelled && attempts < MAX_ATTEMPTS) {
        timer = window.setTimeout(poll, retryDelayMs(attempts));
      } else if (!cancelled) {
        setPhotosPending(false);
      }
    };

    void poll();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [listing.id, listing.source, listing.url, listing.images?.length, visible]);

  return { images, rootRef, photosPending };
}
