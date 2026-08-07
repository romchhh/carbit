"use client";

import { useCallback, useState } from "react";
import type { Listing } from "@/types/api";
import { MAX_COMPARE } from "@/lib/listing-compare";
import { useListingCompare } from "@/hooks/useListingCompare";

export function useCompareOnListingCard() {
  const { compareIds, toggle, isFull } = useListingCompare();
  const [hint, setHint] = useState<string | null>(null);

  const toggleWithHint = useCallback(
    (listing: Listing) => {
      const result = toggle(listing);
      if (!result.ok && result.reason === "full") {
        setHint(`Максимум ${MAX_COMPARE} авто для порівняння — приберіть одне з панелі внизу.`);
        window.setTimeout(() => setHint(null), 4000);
      } else {
        setHint(null);
      }
    },
    [toggle],
  );

  const cardCompareProps = useCallback(
    (listing: Listing) => ({
      isCompared: compareIds.has(listing.id),
      compareDisabled: isFull && !compareIds.has(listing.id),
      onToggleCompare: () => toggleWithHint(listing),
    }),
    [compareIds, isFull, toggleWithHint],
  );

  return { cardCompareProps, compareHint: hint, clearCompareHint: () => setHint(null) };
}
