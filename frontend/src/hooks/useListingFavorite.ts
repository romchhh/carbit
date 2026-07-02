"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, favorites as favoritesApi, getApiErrorMessage } from "@/lib/api";
import { normalizeListingForFavorite } from "@/lib/listing-favorite-payload";
import type { Listing } from "@/types/api";

export const FAVORITES_CHANGED_EVENT = "carbit:favorites-changed";

export function notifyFavoritesChanged() {
  window.dispatchEvent(new CustomEvent(FAVORITES_CHANGED_EVENT));
}

export function useListingFavorites(listingIds: string[]) {
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set());
  const [loadingIds, setLoadingIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const idsKey = listingIds.join("|");

  useEffect(() => {
    if (!idsKey) {
      setFavoriteIds(prev => (prev.size === 0 ? prev : new Set()));
      return;
    }

    let cancelled = false;
    const ids = idsKey.split("|");

    favoritesApi
      .checkMany(ids)
      .then(({ ids: favoriteIdList }) => {
        if (!cancelled) setFavoriteIds(new Set(favoriteIdList));
      })
      .catch(() => {
        if (!cancelled) setFavoriteIds(prev => (prev.size === 0 ? prev : new Set()));
      });

    return () => {
      cancelled = true;
    };
  }, [idsKey]);

  const toggleFavorite = useCallback(async (listing: Listing) => {
    const id = listing.id;
    setError(null);
    setLoadingIds(prev => new Set(prev).add(id));

    let removing = false;
    setFavoriteIds(prev => {
      removing = prev.has(id);
      return prev;
    });

    try {
      if (removing) {
        await favoritesApi.remove(id);
        setFavoriteIds(prev => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      } else {
        await favoritesApi.add(id, normalizeListingForFavorite(listing));
        setFavoriteIds(prev => new Set(prev).add(id));
      }
      notifyFavoritesChanged();
    } catch (err) {
      setError(getApiErrorMessage(err, "Не вдалось оновити обране"));
      if (err instanceof ApiError && err.status === 401) {
        setError("Увійдіть, щоб зберігати авто в обране");
      }
    } finally {
      setLoadingIds(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }, []);

  return {
    favoriteIds,
    loadingIds,
    error,
    clearError: () => setError(null),
    isFavorite: (id: string) => favoriteIds.has(id),
    isLoading: (id: string) => loadingIds.has(id),
    toggleFavorite,
  };
}
