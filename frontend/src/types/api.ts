export interface User {
  id: string;
  email: string;
  name: string;
  plan: string;
  searches_limit: number;
  telegram_connected: boolean;
  telegram_username?: string | null;
  avatar_url?: string | null;
  email_verified?: boolean;
  trial_ends_at?: string | null;
  is_trial_active?: boolean;
  onboarding_completed?: boolean;
  plan_expires_at?: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface SearchQuery {
  id: string;
  name: string;
  filters: Record<string, unknown>;
  is_active: boolean;
  new_count: number;
  total_count: number;
  last_checked_at: string | null;
  created_at: string;
}

export interface Listing {
  id: string;
  source: string;
  title: string;
  brand: string;
  model: string;
  year: number;
  price: number;
  currency: string;
  mileage: number;
  fuel: string;
  transmission: string;
  region: string;
  description?: string | null;
  images: string[];
  url: string;
  seller_type: string;
  price_history: Record<string, unknown>[];
  is_duplicate: boolean;
  published_at: string;
  found_at: string;
}

export interface PaginatedListings {
  items: Listing[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface Favorite {
  id: string;
  listing_id: string;
  listing: Listing;
  created_at: string;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  listing_id: string | null;
  search_id: string | null;
  payload: Record<string, unknown>;
  is_read: boolean;
  sent_telegram: boolean;
  created_at: string;
}

export interface PaginatedNotifications {
  items: Notification[];
  total: number;
  unread: number;
  page: number;
  per_page: number;
}

export interface DashboardStats {
  active_searches: number;
  searches_limit: number;
  new_listings_today: number;
  new_listings_yesterday: number;
  favorites_count: number;
  unread_notifications: number;
  sources_count: number;
  plan: string;
  is_trial_active: boolean;
}

export interface Plan {
  id: string;
  name: string;
  description: string;
  searches_limit: number;
  requests_month: number;
  requests_hour: number;
  price_uah: number;
  features: string[];
}

export interface Subscription {
  plan: string;
  plan_name: string;
  searches_limit: number;
  plan_expires_at: string | null;
  trial_ends_at: string | null;
  is_trial_active: boolean;
}

export interface TelegramConnectLink {
  bot_url: string;
  bot_username: string;
  expires_in: number;
}

export interface TelegramStatus {
  connected: boolean;
  telegram_username: string | null;
  telegram_id: string | null;
}

export interface TelegramRegisterInfo {
  name: string;
  email: string;
  valid: boolean;
  telegram_only?: boolean;
}
