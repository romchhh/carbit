import type { SearchFilterState } from "@/lib/search-catalog";
import { DEFAULT_FILTERS } from "@/lib/search-catalog";
import type { SearchFreshness } from "@/lib/search-preview";

const KEY = "carbit:search-draft";
const POST_AUTH_PATH = "/app/search";

export type SearchDraft = {
  filters: SearchFilterState;
  freshness: SearchFreshness;
};

/** Захист від подвійного запуску в React Strict Mode (живе між remount). */
let draftAutoRunStarted = false;

function parseDraft(raw: string): SearchDraft | null {
  try {
    const parsed = JSON.parse(raw) as Partial<SearchDraft & SearchFilterState>;
    if (parsed && typeof parsed === "object" && parsed.filters && typeof parsed.filters === "object") {
      return {
        filters: { ...DEFAULT_FILTERS, ...parsed.filters },
        freshness: parsed.freshness === "all" ? "all" : "new",
      };
    }
    return {
      filters: { ...DEFAULT_FILTERS, ...parsed },
      freshness: "new",
    };
  } catch {
    return null;
  }
}

export function saveSearchDraft(
  filters: SearchFilterState,
  options?: { freshness?: SearchFreshness },
) {
  if (typeof window === "undefined") return;
  draftAutoRunStarted = false;
  const payload: SearchDraft = {
    filters,
    freshness: options?.freshness === "all" ? "all" : "new",
  };
  sessionStorage.setItem(KEY, JSON.stringify(payload));
}

export function peekSearchDraft(): SearchDraft | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(KEY);
  if (!raw) return null;
  return parseDraft(raw);
}

export function hasSearchDraft(): boolean {
  return peekSearchDraft() !== null;
}

export function clearSearchDraft() {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(KEY);
  draftAutoRunStarted = false;
}

/** Один раз на сесію сторінки — не дублюємо автопошук після remount. */
export function beginSearchDraftAutoRun(): boolean {
  if (draftAutoRunStarted) return false;
  draftAutoRunStarted = true;
  return true;
}

/** Куди вести після входу: збережений пошук важливіший за dashboard. */
export function resolvePostAuthRedirect(explicitRedirect?: string | null): string {
  if (explicitRedirect?.startsWith("/app")) return explicitRedirect;
  if (hasSearchDraft()) return POST_AUTH_PATH;
  return "/app/dashboard";
}
