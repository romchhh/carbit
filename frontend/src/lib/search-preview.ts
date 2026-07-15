export const SEARCH_PAGE_SIZE = 10;
/** Розмір API-сторінки = розмір видимого батча (лінива гідрація get_info). */
export const SEARCH_FIRST_BATCH = SEARCH_PAGE_SIZE;
export const SEARCH_HOURLY_LIMIT = 40;
export const SEARCH_NEW_WITHIN_DAYS = 7;

/** @deprecated Use SEARCH_PAGE_SIZE */
export const PREVIEW_RESULTS_LIMIT = SEARCH_PAGE_SIZE;
/** @deprecated Use SEARCH_HOURLY_LIMIT */
export const PREVIEW_HOURLY_LIMIT = SEARCH_HOURLY_LIMIT;

export type AutoRiaSearchMode = "preview" | "browse";
export type SearchFreshness = "all" | "new";
