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

  const res = await fetch(`${getApiUrl()}${path}`, { ...options, headers });
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
}

export const adminApi = {
  login: (username: string, password: string) =>
    request<{ access_token: string }>("/admin/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
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
  updateUser: (id: string, body: { plan?: string; is_active?: boolean }) =>
    request<AdminUser>(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  subscriptions: () =>
    request<{ plan: string; plan_name: string; count: number; revenue_uah: number }[]>("/admin/subscriptions"),
  finance: () =>
    request<{
      mrr_uah: number; arr_uah: number; trial_count: number; paid_count: number;
      avg_revenue_per_user: number;
      by_plan: { plan: string; plan_name: string; count: number; revenue_uah: number }[];
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
};

export interface AdminParserSettings {
  enabled: boolean;
  interval_seconds: number;
  max_listings_per_group: number;
  cache_ttl_seconds: number;
  notify_telegram: boolean;
  telegram_enabled: boolean;
  telegram_history_limit: number;
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
