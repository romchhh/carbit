import { getAdminToken } from "@/lib/admin-storage";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

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

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
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
};
