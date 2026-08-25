import { clearToken, getToken } from "@/lib/auth-storage";
import { getApiUrl } from "@/lib/api-url";
import { normalizeListingForFavorite } from "@/lib/listing-favorite-payload";
import { cachedAutoRiaSearch } from "@/lib/auto-ria-search-cache";
import type { AutoRiaSearchMode } from "@/lib/search-preview";
import type { SortOption } from "@/lib/search-catalog";
import type { BackendSearchFilters } from "@/lib/search-filters-api";
import { applyFxRates, fxRatesStale } from "@/lib/display-currency";
import type {
  DashboardStats,
  Favorite,
  Listing,
  LiqPayCheckout,
  Notification,
  PaginatedListings,
  PaginatedNotifications,
  Plan,
  SearchLiveResults,
  SearchQuery,
  Subscription,
  TelegramConnectLink,
  TelegramStatus,
  TokenResponse,
  UpgradeQuote,
  User,
  VinCheckHistory,
  VinCheckResult,
  VinQuotaStatus,
  MonitoringSourceRequest,
  SavedComparison,
  SavedComparisonDetail,
  SavedComparisonShare,
} from "@/types/api";

function apiUrl(): string {
  return getApiUrl();
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
    public retryAfter?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getApiErrorMessage(err: unknown, fallback = "Помилка запиту"): string {
  if (err instanceof ApiError) return err.message;
  return fallback;
}

export function isSearchRateLimitError(err: unknown): boolean {
  if (err instanceof ApiError) {
    return err.status === 429 && (err.code === "search_rate_limit" || /ліміт пошуків/i.test(err.message));
  }
  if (typeof err === "string") {
    return /ліміт пошуків/i.test(err);
  }
  return false;
}

type ParsedApiError = {
  message: string;
  code?: string;
  retryAfter?: number;
};

async function parseError(res: Response): Promise<ParsedApiError> {
  let retryAfter: number | undefined;
  const header = res.headers.get("Retry-After");
  if (header) {
    const n = Number(header);
    if (Number.isFinite(n) && n > 0) retryAfter = Math.floor(n);
  }

  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === "string") {
      return { message: detail, retryAfter };
    }
    if (detail && typeof detail === "object" && !Array.isArray(detail)) {
      const message =
        typeof detail.message === "string"
          ? detail.message
          : typeof detail.detail === "string"
            ? detail.detail
            : "Помилка запиту";
      const code = typeof detail.code === "string" ? detail.code : undefined;
      const fromBody =
        typeof detail.retry_after === "number" && detail.retry_after > 0
          ? Math.floor(detail.retry_after)
          : undefined;
      return { message, code, retryAfter: fromBody ?? retryAfter };
    }
    if (Array.isArray(detail)) {
      return {
        message: detail.map((e: { msg?: string }) => e.msg).filter(Boolean).join(", ") || "Помилка запиту",
        retryAfter,
      };
    }
  } catch {
    /* ignore */
  }
  return { message: "Помилка запиту", retryAfter };
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const run = async (withBearer: boolean) => {
    const headers = new Headers(options.headers);
    if (!headers.has("Content-Type") && options.body) headers.set("Content-Type", "application/json");
    if (withBearer) {
      const token = getToken();
      if (token) headers.set("Authorization", `Bearer ${token}`);
    }

    const method = (options.method ?? "GET").toUpperCase();
    return fetch(`${apiUrl()}${path}`, {
      ...options,
      headers,
      credentials: "include",
      redirect: method === "GET" || method === "HEAD" ? "follow" : "manual",
    });
  };

  let res = await run(true);

  // Протухший Bearer + валідна HttpOnly cookie → retry лише з cookie
  if (res.status === 401 && getToken()) {
    clearToken();
    res = await run(false);
  }

  if (res.status >= 300 && res.status < 400) {
    throw new ApiError(res.status, "Некоректне перенаправлення API. Перезберіть backend і frontend.");
  }

  if (!res.ok) {
    const parsed = await parseError(res);
    if (
      res.status === 401 &&
      parsed.message === "Session revoked" &&
      typeof window !== "undefined"
    ) {
      clearToken();
      sessionStorage.setItem("carbit_session_revoked", "1");
      if (window.location.pathname.startsWith("/app")) {
        window.location.assign("/auth/login?session=revoked");
      }
    }
    throw new ApiError(res.status, parsed.message, parsed.code, parsed.retryAfter);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────
export const auth = {
  login: (body: { email: string; password: string; remember?: boolean }) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  logout: () =>
    request<{ message: string }>("/auth/logout", { method: "POST" }),
  oauthExchange: (code: string) =>
    request<TokenResponse>("/auth/oauth/exchange", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  registerSendCode: (body: { email: string; name: string; password: string }) =>
    request<{ message: string }>("/auth/register/send-code", { method: "POST", body: JSON.stringify(body) }),
  registerResendCode: (email: string) =>
    request<{ message: string }>("/auth/register/resend-code", { method: "POST", body: JSON.stringify({ email }) }),
  registerVerify: (body: { email: string; code: string }) =>
    request<TokenResponse>("/auth/register/verify", { method: "POST", body: JSON.stringify(body) }),
  forgotPassword: (email: string) =>
    request<{ message: string }>("/auth/password/forgot", { method: "POST", body: JSON.stringify({ email }) }),
  resetPassword: (token: string, password: string) =>
    request<TokenResponse>("/auth/password/reset", { method: "POST", body: JSON.stringify({ token, password }) }),
  telegramLogin: (token: string) =>
    request<TokenResponse>("/auth/telegram/login", { method: "POST", body: JSON.stringify({ token }) }),
  telegramLoginUrl: () => request<{ bot_url: string; bot_username: string }>("/auth/telegram/login-url"),
  telegramRegisterUrl: () => request<{ bot_url: string; bot_username: string }>("/auth/telegram/register-url"),
  googleLoginUrl: () => `${apiUrl()}/auth/google`,
  phoneSendCode: (body: {
    phone: string;
    intent: "login" | "register";
    name?: string;
    delivery?: "auto" | "sms";
  }) =>
    request<{ message: string; expires_in?: number; channel?: "sms" | "telegram" }>(
      "/auth/phone/send-code",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    ),
  phoneVerify: (body: {
    phone: string;
    code: string;
    intent: "login" | "register";
    name?: string;
    remember?: boolean;
  }) =>
    request<TokenResponse>("/auth/phone/verify", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  phoneLogin: (body: { phone: string; password: string; remember?: boolean }) =>
    request<TokenResponse>("/auth/phone/login", { method: "POST", body: JSON.stringify(body) }),
  setPassword: (body: { password: string; current_password?: string }) =>
    request<User>("/auth/password/set", { method: "POST", body: JSON.stringify(body) }),
  me: () => request<User>("/auth/me"),
  updateProfile: (body: { name?: string; preferred_currency?: string }) =>
    request<User>("/auth/me", { method: "PATCH", body: JSON.stringify(body) }),
};

// ── Users ─────────────────────────────────────────────
export const users = {
  dashboard: () => request<DashboardStats>("/users/me/dashboard"),
  completeOnboarding: () =>
    request<User>("/users/me/onboarding", { method: "POST", body: JSON.stringify({ completed: true }) }),
  sendEmailBindCode: (email: string) =>
    request<{ message: string }>("/users/me/email/send-code", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  verifyEmailBind: (email: string, code: string) =>
    request<User>("/users/me/email/verify", {
      method: "POST",
      body: JSON.stringify({ email, code }),
    }),
  sendPhoneBindCode: (phone: string) =>
    request<{ message: string; expires_in?: number }>("/users/me/phone/send-code", {
      method: "POST",
      body: JSON.stringify({ phone }),
    }),
  verifyPhoneBind: (phone: string, code: string) =>
    request<User>("/users/me/phone/verify", {
      method: "POST",
      body: JSON.stringify({ phone, code }),
    }),
};

// ── Searches ──────────────────────────────────────────
export const searches = {
  list: () => request<SearchQuery[]>("/searches"),
  get: (id: string) => request<SearchQuery>(`/searches/${id}`),
  results: (
    id: string,
    page = 1,
    perPage = 20,
    sortBy: SortOption = "newest",
    options?: { priceDropsOnly?: boolean },
  ) => {
    const params = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
      sort_by: sortBy,
    });
    if (options?.priceDropsOnly) {
      params.set("price_drops_only", "true");
    }
    return request<SearchLiveResults>(`/searches/${id}/results?${params.toString()}`);
  },
  markSeen: (id: string) =>
    request<SearchQuery>(`/searches/${id}/seen`, { method: "POST" }),
  markAllSeen: () =>
    request<{ marked: number }>("/searches/seen-all", { method: "POST" }),
  create: (name: string, filters: BackendSearchFilters, seedListings: Listing[] = []) =>
    request<SearchQuery>("/searches", {
      method: "POST",
      body: JSON.stringify({
        name,
        filters,
        seed_listings: seedListings.slice(0, 40).map(slimListingForSeed),
      }),
    }),
  update: (
    id: string,
    body: { name?: string; is_active?: boolean; filters?: BackendSearchFilters },
  ) =>
    request<SearchQuery>(`/searches/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  delete: (id: string) =>
    request<void>(`/searches/${id}`, { method: "DELETE" }),
};

function slimListingForSeed(listing: Listing): Record<string, unknown> {
  return {
    id: listing.id,
    source: listing.source,
    title: listing.title,
    brand: listing.brand,
    model: listing.model,
    year: listing.year,
    price: listing.price,
    currency: listing.currency,
    mileage: listing.mileage,
    fuel: listing.fuel ?? "",
    transmission: listing.transmission ?? "",
    region: listing.region ?? "",
    description: listing.description ?? null,
    images: Array.isArray(listing.images) ? listing.images.slice(0, 8) : [],
    url: listing.url,
    seller_type: listing.seller_type || "private",
    seller_name: listing.seller_name ?? null,
    seller_phone: listing.seller_phone ?? null,
    seller_telegram: listing.seller_telegram ?? null,
    seller_url: listing.seller_url ?? null,
    vin: listing.vin ?? null,
    source_data: null,
    price_history: [],
    is_duplicate: listing.is_duplicate ?? false,
    duplicate_of: listing.duplicate_of ?? null,
    alternate_sources: Array.isArray(listing.alternate_sources)
      ? listing.alternate_sources
          .filter((row) => row?.source && row?.url)
          .slice(0, 6)
          .map((row) => ({
            source: row.source,
            url: row.url,
            id: row.id ?? null,
          }))
      : [],
    published_at: listing.published_at,
    refreshed_at: listing.refreshed_at ?? null,
    found_at: listing.found_at,
  };
}

// ── Listings ──────────────────────────────────────────
export const listings = {
  get: (id: string) => request<Listing>(`/listings/${id}`),
  batch: (ids: string[]) =>
    request<Listing[]>(`/listings/batch?ids=${encodeURIComponent(ids.join(","))}`),
  ensurePhotos: (id: string) =>
    request<Listing>(`/listings/${id}/ensure-photos`, { method: "POST" }),
};

// ── Live search (AUTO.RIA + OLX) ──────────────────────
export const listingSearch = {
  search: (
    filters: BackendSearchFilters,
    page = 1,
    perPage = 20,
    sortBy: SortOption = "newest",
    mode: AutoRiaSearchMode = "preview",
    signal?: AbortSignal,
  ) =>
    cachedAutoRiaSearch(
      { filters, page, perPage, sortBy, mode },
      () =>
        request<PaginatedListings>(
          `/searches/live?page=${page}&per_page=${perPage}&sort_by=${sortBy}&mode=${mode}`,
          { method: "POST", body: JSON.stringify(filters), signal },
        ),
      signal,
    ),
};

export const fx = {
  rates: async () => {
    if (!fxRatesStale()) return;
    try {
      const data = await request<{ USD?: number; EUR?: number }>("/fx/rates");
      applyFxRates(data);
    } catch {
      /* fallback constants */
    }
  },
};

/** @deprecated Use listingSearch.search */
export const autoRia = listingSearch;

// ── Favorites ─────────────────────────────────────────
export const favorites = {
  list: () => request<Favorite[]>("/favorites/list"),
  add: (listingId: string, listing?: Listing) =>
    request<Favorite>("/favorites/add", {
      method: "POST",
      body: JSON.stringify(
        listing
          ? { listing_id: listingId, listing: normalizeListingForFavorite(listing) }
          : { listing_id: listingId },
      ),
    }),
  remove: (listingId: string) => request<void>(`/favorites/${listingId}`, { method: "DELETE" }),
  check: (listingId: string) => request<{ is_favorite: boolean }>(`/favorites/check/${listingId}`),
  checkMany: (listingIds: string[]) =>
    request<{ ids: string[] }>("/favorites/check", {
      method: "POST",
      body: JSON.stringify({ listing_ids: listingIds }),
    }),
};

// ── Notifications ─────────────────────────────────────
export const notifications = {
  list: (page = 1, unreadOnly = false, sortBy: SortOption = "newest", perPage = 20) =>
    request<PaginatedNotifications>(
      `/notifications?page=${page}&per_page=${perPage}&unread_only=${unreadOnly}&sort_by=${sortBy}`,
    ),
  stats: () => request<{ unread: number; total: number }>("/notifications/stats"),
  markRead: (id: string) => request<Notification>(`/notifications/${id}/read`, { method: "PATCH" }),
  markAllRead: () => request<{ marked: number }>("/notifications/read-all", { method: "POST" }),
  seedDemo: () => request<{ listings_created: number; notifications_sent: number }>("/notifications/demo/seed", { method: "POST" }),
};

// ── Billing ───────────────────────────────────────────
export const billing = {
  plans: () => request<Plan[]>("/billing/plans"),
  subscription: () => request<Subscription>("/billing/subscription"),
  subscribe: (plan: string) =>
    request<Subscription>("/billing/subscribe", { method: "POST", body: JSON.stringify({ plan }) }),
  checkout: (plan: string, applyCredit = true) =>
    request<LiqPayCheckout>("/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan, apply_credit: applyCredit }),
    }),
  upgradeQuote: (plan?: string) =>
    request<UpgradeQuote>(
      plan ? `/billing/upgrade-quote?plan=${encodeURIComponent(plan)}` : "/billing/upgrade-quote",
    ),
  unsubscribe: (body?: { reason?: string; note?: string }) =>
    request<Subscription>("/billing/unsubscribe", {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),
};

// ── Telegram ──────────────────────────────────────────
export const telegram = {
  connectLink: () => request<TelegramConnectLink>("/telegram/connect-link"),
  status: () => request<TelegramStatus>("/telegram/status"),
  disconnect: () => request<void>("/telegram/disconnect", { method: "DELETE" }),
  registerComplete: (token: string) =>
    request<{ access_token: string; user: User }>("/telegram/register/complete", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
};

// ── VIN / База ДАІ ────────────────────────────────────
export const vin = {
  lookup: (vinCode: string) => request<VinCheckResult>(`/vin/${encodeURIComponent(vinCode)}`),
  quota: () => request<VinQuotaStatus>("/vin/quota"),
  myHistory: (limit = 20) =>
    request<VinCheckHistory>(`/vin/history/me?limit=${encodeURIComponent(String(limit))}`),
  recentHistory: (limit = 20) =>
    request<VinCheckHistory>(`/vin/history/recent?limit=${encodeURIComponent(String(limit))}`),
};

// ── Заявки на джерела ─────────────────────────────────
export const sourceRequests = {
  list: () => request<MonitoringSourceRequest[]>("/source-requests"),
  create: (body: { url: string; comment?: string }) =>
    request<MonitoringSourceRequest>("/source-requests", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export const comparisons = {
  list: () => request<SavedComparison[]>("/comparisons"),
  create: (body: { name?: string; listing_ids: string[] }) =>
    request<SavedComparison>("/comparisons", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  get: (id: string) => request<SavedComparisonDetail>(`/comparisons/${id}`),
  getShare: (shareId: string) => request<SavedComparisonShare>(`/comparisons/share/${shareId}`),
  remove: (id: string) => request<void>(`/comparisons/${id}`, { method: "DELETE" }),
};

export type AiSearchIntent = "market_discovery" | null;

export type AiParseSearchResult = {
  understood: boolean;
  message: string;
  transcript: string;
  filters: Record<string, unknown>;
  /** Пошук по ринку без марки (бюджет + роки). */
  search_intent?: AiSearchIntent;
  /** Рекомендоване сортування результатів. */
  sort?: SortOption | null;
};

export const ai = {
  parseSearch: (text: string) =>
    request<AiParseSearchResult>("/ai/parse-search", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  transcribeSearch: async (blob: Blob): Promise<AiParseSearchResult> => {
    const form = new FormData();
    form.append("audio", blob, blob.type.includes("mp4") ? "voice.m4a" : "voice.webm");

    const headers = new Headers();
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);

    const res = await fetch(`${apiUrl()}/ai/transcribe-search`, {
      method: "POST",
      body: form,
      headers,
      credentials: "include",
    });

    if (!res.ok) {
      const parsed = await parseError(res);
      throw new ApiError(res.status, parsed.message, parsed.code, parsed.retryAfter);
    }

    return res.json() as Promise<AiParseSearchResult>;
  },
};
