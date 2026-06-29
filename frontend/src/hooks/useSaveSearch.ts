"use client";

import { useCallback, useState } from "react";
import { ApiError, searches as searchesApi } from "@/lib/api";
import type { SearchFilterState } from "@/lib/search-catalog";
import { buildSearchName, toBackendSearchFilters } from "@/lib/search-filters-api";
import type { SearchQuery } from "@/types/api";

function isPlanLimitError(err: unknown): boolean {
  if (!(err instanceof ApiError)) return false;
  if (err.status === 403) return true;
  return /plan limit|ліміт|limit reached/i.test(err.message);
}

export function useSaveSearch(onSaved?: (search: SearchQuery) => void) {
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveLimitReached, setSaveLimitReached] = useState(false);

  const saveSearch = useCallback(async (filters: SearchFilterState) => {
    setSaving(true);
    setSaveSuccess(null);
    setSaveError(null);
    setSaveLimitReached(false);
    try {
      const created = await searchesApi.create(buildSearchName(filters), toBackendSearchFilters(filters));
      setSaveSuccess("Пошук збережено! Нові авто з’являться у Telegram та в «Мої запити».");
      onSaved?.(created);
    } catch (err) {
      if (isPlanLimitError(err)) {
        setSaveLimitReached(true);
        setSaveError(null);
      } else {
        setSaveError(err instanceof ApiError ? err.message : "Не вдалось зберегти пошук");
      }
    } finally {
      setSaving(false);
    }
  }, [onSaved]);

  const clearSaveMessages = useCallback(() => {
    setSaveSuccess(null);
    setSaveError(null);
    setSaveLimitReached(false);
  }, []);

  return { saveSearch, saving, saveSuccess, saveError, saveLimitReached, clearSaveMessages };
}
