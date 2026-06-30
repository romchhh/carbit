"use client";

import { useCallback, useEffect, useState } from "react";
import { favorites as favoritesApi } from "@/lib/api";
import type { Listing } from "@/types/api";

export const FAVORITES_CHANGED_EVENT = "carbit:favorites-changed";

export function notifyFavoritesChanged() {
  window.dispatchEvent(new CustomEvent(FAVORITES_CHANGED_EVENT));
}

export function useListingFavorites(listingIds: string[]) {
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set());
  const [loadingIds, setLoadingIds] = useState<Set<string>>(new Set());

  const idsKey = listingIds.join("|");

  useEffect(() => {
    if (!listingIds.length) {
      setFavoriteIds(new Set());
      return;
    }

    favoritesApi
      .checkMany(listingIds)
      .then(ids => setFavoriteIds(new Set(ids)))
      .catch(() => setFavoriteIds(new Set()));
  }, [idsKey, listingIds]);

  const toggleFavorite = useCallback(async (listing: Listing) => {
    const id = listing.id;
    setLoadingIds(prev => new Set(prev).add(id));

    try {
      if (favoriteIds.has(id)) {
        await favoritesApi.remove(id);
        setFavoriteIds(prev => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      } else {
        await favoritesApi.add(id, listing);
        setFavoriteIds(prev => new Set(prev).add(id));
      }
      notifyFavoritesChanged();
    } finally {
      setLoadingIds(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }, [favoriteIds]);

  return {
    favoriteIds,
    loadingIds,
    isFavorite: (id: string) => favoriteIds.has(id),
    isLoading: (id: string) => loadingIds.has(id),
    toggleFavorite,
  };
}
