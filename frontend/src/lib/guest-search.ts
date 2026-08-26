export const GUEST_SEARCH_LIMIT = 3;

const COUNT_KEY = "carbit:guest-search-count";

export function getGuestSearchCount(): number {
  if (typeof window === "undefined") return 0;
  const raw = window.localStorage.getItem(COUNT_KEY);
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? Math.min(parsed, GUEST_SEARCH_LIMIT) : 0;
}

export function getGuestSearchesRemaining(): number {
  return Math.max(0, GUEST_SEARCH_LIMIT - getGuestSearchCount());
}

export function canGuestSearch(): boolean {
  return getGuestSearchesRemaining() > 0;
}

export function syncGuestSearchQuota(remaining: number | null | undefined, limit = GUEST_SEARCH_LIMIT) {
  if (typeof window === "undefined") return;
  if (remaining == null || !Number.isFinite(remaining)) return;
  const used = Math.max(0, Math.min(limit, limit - remaining));
  window.localStorage.setItem(COUNT_KEY, String(used));
}

export function markGuestSearchUsed() {
  if (typeof window === "undefined") return;
  const next = Math.min(GUEST_SEARCH_LIMIT, getGuestSearchCount() + 1);
  window.localStorage.setItem(COUNT_KEY, String(next));
}
