"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { Listing } from "@/types/api";
import {
  COMPARE_CHANGED_EVENT,
  MAX_COMPARE,
  addCompareListing,
  clearCompareListings,
  loadCompareListings,
  removeCompareListing,
  toggleCompareListing,
  type CompareAddResult,
} from "@/lib/listing-compare";

export function useListingCompare() {
  const [items, setItems] = useState<Listing[]>([]);

  const refresh = useCallback(() => {
    setItems(loadCompareListings());
  }, []);

  useEffect(() => {
    refresh();
    window.addEventListener(COMPARE_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(COMPARE_CHANGED_EVENT, refresh);
  }, [refresh]);

  const compareIds = useMemo(() => new Set(items.map(item => item.id)), [items]);

  const toggle = useCallback((listing: Listing): CompareAddResult | { ok: true; removed: true } => {
    const result = toggleCompareListing(listing);
    refresh();
    return result;
  }, [refresh]);

  const add = useCallback((listing: Listing): CompareAddResult => {
    const result = addCompareListing(listing);
    refresh();
    return result;
  }, [refresh]);

  const remove = useCallback((id: string) => {
    removeCompareListing(id);
    refresh();
  }, [refresh]);

  const clear = useCallback(() => {
    clearCompareListings();
    refresh();
  }, [refresh]);

  return {
    items,
    count: items.length,
    compareIds,
    toggle,
    add,
    remove,
    clear,
    max: MAX_COMPARE,
    isFull: items.length >= MAX_COMPARE,
    refresh,
  };
}
