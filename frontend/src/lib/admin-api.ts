import { getAdminToken } from "@/lib/admin-storage";
import { getApiUrl } from "@/lib/api-url";

export class AdminApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAdminToken();
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${getApiUrl()}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });
  if (!res.ok) {
    let msg = "Помилка запиту";
    try { const b = await res.json(); if (b.detail) msg = b.detail; } catch { /* */ }
    throw new AdminApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface AdminDashboard {
  total_users: number;
  new_users_today: number;
  new_users_week: number;
  active_subscriptions: number;
  trial_users: number;
  telegram_connected: number;
  total_searches: number;
  total_notifications: number;
  revenue_month_uah: number;
  plan_breakdown: Record<string, number>;
  registrations_chart: { date: string; count: number }[];
  liqpay_active?: number;
  liqpay_past_due?: number;
  expiring_7d?: number;
  expired_plans?: number;
  recurring_mrr_uah?: number;
}

export interface AdminBillingSubscription {
  id: string;
  order_id: string;
  plan: string;
  plan_name: string;
  amount: number;
  currency: string;
  periodicity: string;
  status: string;
  last_status?: string | null;
  failed_charges: number;
  liqpay_payment_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  cancelled_at?: string | null;
  user_id?: string | null;
  user_name?: string | null;
  user_email?: string | null;
}

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  plan: string;
  telegram_connected: boolean;
  telegram_username: string | null;
  is_active: boolean;
  is_trial_active: boolean;
  searches_count: number;
  created_at: string;
  avatar_url?: string | null;
}

export interface AdminUserDetail extends AdminUser {
  trial_ends_at: string | null;
  plan_expires_at: string | null;
  notifications_count: number;
  favorites_count: number;
  searches: { id: string; name: string; is_active: boolean; new_count: number; total_count: number }[];
  billing_subscriptions?: AdminBillingSubscription[];
  billing_summary?: {
    active_recurring: boolean;
    past_due: boolean;
    plan_expired: boolean;
    failed_charges: number;
    subscriptions_count: number;
  };
}

export const adminApi = {
  login: (username: string, password: string) =>
    request<{ access_token: string }>("/admin/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () =>
    request<{ message: string }>("/admin/auth/logout", { method: "POST" }),
  me: () => request<{ ok: boolean; role: string }>("/admin/auth/me"),
  dashboard: () => request<AdminDashboard>("/admin/dashboard"),
  users: (page = 1, search = "", plan = "") => {
    const params = new URLSearchParams({ page: String(page), per_page: "20" });
    if (search) params.set("search", search);
    if (plan) params.set("plan", plan);
    return request<{ items: AdminUser[]; total: number; page: number; per_page: number }>(
      `/admin/users?${params}`,
    );
  },
  user: (id: string) => request<AdminUserDetail>(`/admin/users/${id}`),
  updateUser: (
    id: string,
    body: {
      plan?: string;
      is_active?: boolean;
      access_months?: number;
      access_days?: number;
    },
  ) =>
    request<AdminUser>(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteUser: (id: string) =>
    request<{ message: string }>(`/admin/users/${id}`, { method: "DELETE" }),
  subscriptions: () =>
    request<{ plan: string; plan_name: string; count: number; revenue_uah: number }[]>("/admin/subscriptions"),
  finance: () =>
    request<{
      mrr_uah: number;
      arr_uah: number;
      trial_count: number;
      paid_count: number;
      avg_revenue_per_user: number;
      by_plan: { plan: string; plan_name: string; count: number; revenue_uah: number }[];
      liqpay?: {
        by_status: Record<string, number>;
        active_recurring: number;
        past_due: number;
        failed: number;
        cancelled: number;
        pending: number;
        recurring_mrr_uah: number;
        failed_charges_total: number;
        expired_plans: number;
        expiring_7d: number;
      } | null;
      issues?: AdminBillingSubscription[];
    }>("/admin/finance"),
  parserSettings: () => request<AdminParserSettings>("/admin/parser/settings"),
  updateParserSettings: (body: Partial<AdminParserSettings>) =>
    request<AdminParserSettings>("/admin/parser/settings", { method: "PATCH", body: JSON.stringify(body) }),
  parserStats: () => request<AdminParserStats>("/admin/parser/stats"),
  parserRuns: (limit = 30) => request<AdminParseRun[]>(`/admin/parser/runs?limit=${limit}`),
  parserListings: (limit = 40) =>
    request<Array<Record<string, unknown>>>(`/admin/parser/listings?limit=${limit}`),
  parserNotifications: (limit = 50, runId?: string) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (runId) params.set("run_id", runId);
    return request<AdminParserNotification[]>(`/admin/parser/notifications?${params}`);
  },
  triggerParserRun: () => request<AdminParseRun>("/admin/parser/run", { method: "POST" }),
  triggerParserRunSource: (source: "auto_ria" | "olx" | "telegram") =>
    request<AdminParseRun>(`/admin/parser/run/${source}`, { method: "POST" }),
  telegramWorkerStatus: () => request<AdminTelegramWorkerStatus>("/admin/parser/telegram/status"),
  telethonSessionStatus: () => request<AdminTelethonSessionStatus>("/admin/parser/telethon/session"),
  telethonResetSession: () =>
    request<AdminTelethonSessionReset>("/admin/parser/telethon/session/reset", { method: "POST" }),
  telethonSendCode: () =>
    request<AdminTelethonAuthResult>("/admin/parser/telethon/auth/send-code", { method: "POST" }),
  telethonSignIn: (code: string) =>
    request<AdminTelethonAuthResult>("/admin/parser/telethon/auth/sign-in", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  telethonPassword: (password: string) =>
    request<AdminTelethonAuthResult>("/admin/parser/telethon/auth/password", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
  telegramChannels: () => request<AdminTelegramChannel[]>("/admin/parser/channels"),
  createTelegramChannel: (body: { username: string; title?: string; enabled?: boolean }) =>
    request<AdminTelegramChannel>("/admin/parser/channels", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateTelegramChannel: (
    id: string,
    body: { username?: string; title?: string | null; enabled?: boolean; sort_order?: number },
  ) =>
    request<AdminTelegramChannel>(`/admin/parser/channels/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteTelegramChannel: (id: string) =>
    request<void>(`/admin/parser/channels/${id}`, { method: "DELETE" }),
  telegramChannelListings: (id: string, limit = 40) =>
    request<Array<Record<string, unknown>>>(`/admin/parser/channels/${id}/listings?limit=${limit}`),
  analytics: () => request<AdminAnalytics>("/admin/analytics"),
  system: () => request<AdminSystem>("/admin/system"),
  listingsBrowse: (page = 1, opts: { source?: string; search?: string; duplicates_only?: boolean } = {}) => {
    const params = new URLSearchParams({ page: String(page), per_page: "30" });
    if (opts.source) params.set("source", opts.source);
    if (opts.search) params.set("search", opts.search);
    if (opts.duplicates_only) params.set("duplicates_only", "true");
    return request<{ items: AdminListingRow[]; total: number; page: number; per_page: number }>(
      `/admin/listings?${params}`,
    );
  },
  listing: (id: string) => request<AdminListingDetail>(`/admin/listings/${id}`),
};

export interface AdminParserSettings {
  enabled: boolean;
  interval_seconds: number;
  max_listings_per_group: number;
  cache_ttl_seconds: number;
  notify_telegram: boolean;
  telegram_enabled: boolean;
  telegram_history_limit: number;
  telegram_worker_poll_seconds: number;
  telegram_channel_sync_seconds: number;
  notification_max_published_hours: number;
}

export interface AdminTelegramWorkerStatus {
  telegram_enabled: boolean;
  telethon_configured: boolean;
  worker_online: boolean;
  worker_heartbeat_age_seconds: number | null;
  interval_seconds: number;
  telegram_worker_poll_seconds: number;
  telegram_channel_sync_seconds: number;
  telegram_history_limit: number;
  keyword_queue: { pending: number; running: number; done: number; error: number };
  schedule_hint: string;
}

export interface AdminTelethonSessionStatus {
  telethon_configured: boolean;
  phone_configured: boolean;
  phone_masked: string;
  session_file: string;
  session_exists: boolean;
  authorized: boolean;
  user: { id: number; first_name: string; username: string | null } | null;
  error: string | null;
  error_code: string | null;
  auth_step: string | null;
  session_note?: string | null;
  worker_holds_session?: boolean;
}

export interface AdminTelethonAuthResult {
  status: string;
  phone_masked?: string | null;
  user?: { id: number; first_name: string; username: string | null } | null;
}

export interface AdminTelethonSessionReset {
  removed: string[];
  session_file: string;
}

export interface AdminParseRun {
  id: string;
  status: string;
  triggered_by: string;
  filter_groups: number;
  searches_processed: number;
  listings_found: number;
  listings_new: number;
  notifications_sent: number;
  error: string | null;
  log: string[];
  started_at: string;
  finished_at: string | null;
}

export interface AdminParserStats {
  active_searches: number;
  total_search_listings: number;
  total_listings: number;
  total_telegram_sent: number;
  last_run: AdminParseRun | null;
  settings: AdminParserSettings;
}

export interface AdminParserNotification {
  id: string;
  sent_at: string;
  user_id: string;
  user_name: string;
  user_email: string;
  telegram_username: string | null;
  search_id: string | null;
  search_name: string | null;
  listing_id: string | null;
  listing_title: string;
  listing_brand: string | null;
  listing_model: string | null;
  listing_year: number | null;
  listing_price: number | null;
  listing_region: string | null;
  listing_source: string | null;
  listing_url: string | null;
  listing_image: string | null;
}

export interface AdminTelegramChannel {
  id: string;
  username: string;
  title: string | null;
  enabled: boolean;
  sort_order: number;
  listings_count: number;
  created_at: string;
}

export interface AdminAnalytics {
  listings_by_source: Record<string, number>;
  total_listings: number;
  duplicate_listings: number;
  listings_today: number;
  listings_week: number;
  notifications_today: number;
  notifications_week: number;
  active_searches: number;
  inactive_searches: number;
  favorites_count: number;
  listings_chart: { date: string; count: number }[];
  notifications_chart: { date: string; count: number }[];
  parse_runs_chart: {
    date: string;
    runs: number;
    success: number;
    failed: number;
    partial: number;
    listings_found: number;
    listings_new: number;
  }[];
  data_quality?: Record<
    string,
    {
      total: number;
      with_vin: number;
      with_price: number;
      with_published_at: number;
      pct_vin: number;
      pct_price: number;
      pct_published_at: number;
    }
  >;
}

export interface AdminSystem {
  database_ok: boolean;
  kv_store_ok: boolean;
  integrations: { key: string; name: string; ok: boolean; detail: string }[];
  parser_settings: AdminParserSettings;
  telegram_channels: number;
  last_run: {
    id: string;
    status: string;
    started_at: string;
    finished_at: string | null;
    listings_found: number;
    listings_new: number;
    notifications_sent: number;
    error: string | null;
  } | null;
  scheduler_status: string;
  seconds_since_last_run: number | null;
  running_parse_jobs: number;
  frontend_url: string;
  debug_mode: boolean;
}

export interface AdminListingRow {
  id: string;
  external_id: string;
  source: string;
  title: string;
  brand: string;
  model: string;
  year: number;
  price: number;
  region: string;
  url: string;
  image: string | null;
  is_duplicate: boolean;
  found_at: string;
}

export type AdminListingDetail = import("@/types/api").Listing;
