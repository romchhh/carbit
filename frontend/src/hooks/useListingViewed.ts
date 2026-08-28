"use client";

import { useEffect, useState } from "react";
import {
  isListingViewed,
  VIEWED_LISTINGS_CHANGED_EVENT,
} from "@/lib/viewed-listings";

export function useListingViewed(listingId: string): boolean {
  const [viewed, setViewed] = useState(false);

  useEffect(() => {
    const sync = () => setViewed(isListingViewed(listingId));
    sync();
    window.addEventListener(VIEWED_LISTINGS_CHANGED_EVENT, sync);
    return () => window.removeEventListener(VIEWED_LISTINGS_CHANGED_EVENT, sync);
  }, [listingId]);

  return viewed;
}
