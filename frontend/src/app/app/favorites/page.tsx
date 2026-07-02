"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { IconHeart } from "@/components/icons";
import { ListingCard } from "@/components/listings/ListingCard";
import { ListingDetailModal } from "@/components/listings/ListingDetailModal";
import { FAVORITES_CHANGED_EVENT, useListingFavorites } from "@/hooks/useListingFavorite";
import { favorites as favoritesApi } from "@/lib/api";
import { saveRecentListing } from "@/lib/recent-listings";
import { AppEmpty, AppLoading, AppPage } from "@/components/layout/AppPage";
import type { Favorite, Listing } from "@/types/api";

export default function FavoritesPage() {
  const [items, setItems] = useState<Favorite[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);

  const listings = useMemo(() => items.map(item => item.listing), [items]);
  const listingIds = useMemo(() => listings.map(item => item.id), [listings]);
  const { favoriteIds, loadingIds, error: favoriteError, clearError, toggleFavorite } =
    useListingFavorites(listingIds);

  const load = useCallback(async () => {
    try {
      setItems(await favoritesApi.list());
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const onChange = () => {
      void load();
    };
    window.addEventListener(FAVORITES_CHANGED_EVENT, onChange);
    return () => window.removeEventListener(FAVORITES_CHANGED_EVENT, onChange);
  }, [load]);

  const openListing = (listing: Listing) => {
    saveRecentListing(listing);
    setSelectedListing(listing);
  };

  const handleToggleFavorite = async (listing: Listing) => {
    const wasFavorite = favoriteIds.has(listing.id);
    await toggleFavorite(listing);
    if (wasFavorite) {
      setItems(prev => prev.filter(item => item.listing_id !== listing.id));
      if (selectedListing?.id === listing.id) {
        setSelectedListing(null);
      }
    }
  };

  if (loading) return <AppLoading />;

  return (
    <AppPage title="Обране" description="Збережені авто для швидкого доступу">
      {listings.length === 0 ? (
        <AppEmpty>
          <IconHeart size={32} className="mx-auto mb-4 text-muted/30" />
          <p className="text-muted">Поки що немає обраних авто</p>
          <Link href="/app/dashboard" className="mt-4 inline-block">
            <Button variant="primary" size="md">
              До пошуків
            </Button>
          </Link>
        </AppEmpty>
      ) : (
        <div className="-mx-1 flex flex-col gap-3 px-1 sm:mx-0 sm:px-0">
          {listings.map(listing => (
            <ListingCard
              key={listing.id}
              listing={listing}
              onClick={() => openListing(listing)}
              isFavorite={favoriteIds.has(listing.id)}
              favoriteLoading={loadingIds.has(listing.id)}
              onToggleFavorite={() => void handleToggleFavorite(listing)}
            />
          ))}
        </div>
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
          selectedListing ? () => void handleToggleFavorite(selectedListing) : undefined
        }
        favoriteError={favoriteError}
      />
    </AppPage>
  );
}
