export const SEARCH_PAGE_SIZE = 20;
/** Перший запит — одразу до 20 карток (preview max на бекенді). */
export const SEARCH_FIRST_BATCH = 20;
/** Орієнтир для UI (free). На підписці ліміт вищий — див. live_searches_hour у плані. */
export const SEARCH_HOURLY_LIMIT = 30;
export const SEARCH_NEW_WITHIN_DAYS = 7;

/** @deprecated Use SEARCH_PAGE_SIZE */
export const PREVIEW_RESULTS_LIMIT = SEARCH_PAGE_SIZE;
/** @deprecated Use SEARCH_HOURLY_LIMIT */
export const PREVIEW_HOURLY_LIMIT = SEARCH_HOURLY_LIMIT;

export type AutoRiaSearchMode = "preview" | "browse";
export type SearchFreshness = "all" | "new";
