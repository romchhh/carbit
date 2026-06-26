import { getToken } from "@/lib/auth-storage";
import type {
  DashboardStats,
  Favorite,
  Listing,
  Notification,
  PaginatedNotifications,
  Plan,
  SearchQuery,
  Subscription,
  TelegramConnectLink,
  TelegramStatus,
  TokenResponse,
  User,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((e: { msg?: string }) => e.msg).filter(Boolean).join(", ") || "Помилка запиту";
    }
  } catch { /* ignore */ }
  return "Помилка запиту";
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────
export const auth = {
  login: (body: { email: string; password: string }) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
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
  googleLoginUrl: () => `${API_URL}/auth/google`,
  me: () => request<User>("/auth/me"),
  updateProfile: (name: string) =>
    request<User>("/auth/me", { method: "PATCH", body: JSON.stringify({ name }) }),
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
};

// ── Searches ──────────────────────────────────────────
export const searches = {
  list: () => request<SearchQuery[]>("/searches/"),
};

// ── Listings ──────────────────────────────────────────
export const listings = {
  get: (id: string) => request<Listing>(`/listings/${id}`),
};

// ── Favorites ─────────────────────────────────────────
export const favorites = {
  list: () => request<Favorite[]>("/favorites/"),
  add: (listingId: string) =>
    request<Favorite>("/favorites/", { method: "POST", body: JSON.stringify({ listing_id: listingId }) }),
  remove: (listingId: string) => request<void>(`/favorites/${listingId}`, { method: "DELETE" }),
  check: (listingId: string) => request<{ is_favorite: boolean }>(`/favorites/check/${listingId}`),
};

// ── Notifications ─────────────────────────────────────
export const notifications = {
  list: (page = 1, unreadOnly = false) =>
    request<PaginatedNotifications>(`/notifications/?page=${page}&unread_only=${unreadOnly}`),
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
