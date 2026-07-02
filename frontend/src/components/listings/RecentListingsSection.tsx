"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ListingCard } from "@/components/listings/ListingCard";
import { ListingDetailModal } from "@/components/listings/ListingDetailModal";
import { useListingFavorites } from "@/hooks/useListingFavorite";
import { loadRecentListings, saveRecentListing } from "@/lib/recent-listings";
import type { Listing } from "@/types/api";

type Props = {
  limit?: number;
  className?: string;
};

export function RecentListingsSection({ limit = 6, className }: Props) {
  const [items, setItems] = useState<Listing[]>([]);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const { favoriteIds, loadingIds, error: favoriteError, clearError, toggleFavorite } = useListingFavorites(items.map(item => item.id));

  useEffect(() => {
    const sync = () => setItems(loadRecentListings().slice(0, limit));
    sync();
    window.addEventListener("carbit:recent-listings-changed", sync);
    return () => window.removeEventListener("carbit:recent-listings-changed", sync);
  }, [limit]);

  if (items.length === 0) return null;

  const openListing = (listing: Listing) => {
    saveRecentListing(listing);
    setSelectedListing(listing);
  };

  return (
    <>
      <section className={className}>
        <div className="mb-4 flex items-end justify-between gap-3">
          <div>
            <h2 className="text-[17px] font-bold text-ink">Останні переглянуті</h2>
            <p className="mt-1 text-[13px] text-muted">Пропозиції, які ви відкривали нещодавно</p>
          </div>
          <Link href="/app/favorites" className="shrink-0 text-[12px] font-semibold text-emerald-dark hover:underline">
            Обране →
          </Link>
        </div>

        <div className="flex flex-col gap-3">
          {items.map(listing => (
            <ListingCard
              key={listing.id}
              listing={listing}
              onClick={() => openListing(listing)}
              isFavorite={favoriteIds.has(listing.id)}
              favoriteLoading={loadingIds.has(listing.id)}
              onToggleFavorite={() => toggleFavorite(listing)}
            />
          ))}
        </div>
      </section>

      <ListingDetailModal
        listing={selectedListing}
        onClose={() => {
          clearError();
          setSelectedListing(null);
        }}
        isFavorite={selectedListing ? favoriteIds.has(selectedListing.id) : false}
        favoriteLoading={selectedListing ? loadingIds.has(selectedListing.id) : false}
        onToggleFavorite={selectedListing ? () => toggleFavorite(selectedListing) : undefined}
        favoriteError={favoriteError}
      />
    </>
  );
}
