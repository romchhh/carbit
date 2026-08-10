"use client";

import { useEffect, useRef, useState } from "react";
import { listings as listingsApi } from "@/lib/api";
import type { Listing } from "@/types/api";

const inflight = new Map<string, Promise<Listing>>();

function ensurePhotosDeduped(id: string): Promise<Listing> {
  let pending = inflight.get(id);
  if (!pending) {
    pending = listingsApi.ensurePhotos(id).finally(() => {
      inflight.delete(id);
    });
    inflight.set(id, pending);
  }
  return pending;
}

function listingNeedsPhotoHydration(listing: Listing): boolean {
  if ((listing.source || "").toLowerCase() !== "telegram") return false;
  return !(listing.images?.length ?? 0);
}

/** Підвантажує мінімум 1 фото для Telegram-карток у каталозі (лише видимі). */
export function useListingPhotoHydration(listing: Listing) {
  const rootRef = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);
  const [images, setImages] = useState<string[]>(
    Array.isArray(listing.images) ? listing.images : [],
  );

  useEffect(() => {
    setImages(Array.isArray(listing.images) ? listing.images : []);
  }, [listing.id]);

  useEffect(() => {
    if (listing.images?.length) {
      setImages(listing.images);
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
      { rootMargin: "120px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [listing.id]);

  useEffect(() => {
    if (!visible || !listingNeedsPhotoHydration(listing)) return;

    let cancelled = false;
    let attempts = 0;
    let timer: number | undefined;

    const poll = async () => {
      try {
        const fresh =
          attempts === 0
            ? await ensurePhotosDeduped(listing.id)
            : await listingsApi.get(listing.id);
        if (cancelled) return;
        if (fresh.images?.length) {
          setImages(fresh.images);
          return;
        }
      } catch {
        /* worker обробляє чергу фото */
      }

      attempts += 1;
      if (!cancelled && attempts < 40) {
        timer = window.setTimeout(poll, 2000);
      }
    };

    void poll();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [listing.id, listing.source, listing.images?.length, visible]);

  return { images, rootRef };
}
