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
  preferred_currency?: string;
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
  /** Фото найновішого авто в моніторингу. */
  preview_image?: string | null;
}

export interface ListingSourceLink {
  source: string;
  url: string;
  id?: string | null;
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
  vin?: string | null;
  vin_checked?: boolean | null;
  vin_check_url?: string | null;
  source_data?: Record<string, unknown> | null;
  price_history: Record<string, unknown>[];
  is_duplicate: boolean;
  duplicate_of?: string | null;
  /** Інші джерела того самого авто (іконки-посилання в UI). */
  alternate_sources?: ListingSourceLink[];
  /** У результатах моніторингу — нове з моменту збереження / останнього перегляду. */
  is_new?: boolean | null;
  published_at: string;
  refreshed_at?: string | null;
  found_at: string;
}

export interface SourceStatus {
  source: string;
  item_count: number;
  error?: string | null;
  pending?: boolean;
}

export interface PaginatedListings {
  items: Listing[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  sources?: SourceStatus[];
  partial?: boolean;
  from_cache?: boolean;
}

export interface SearchLiveResults {
  search: SearchQuery;
  results: PaginatedListings;
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
  listing?: Listing | null;
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

export interface BillingPayment {
  id: string;
  order_id: string;
  plan: string;
  plan_name: string;
  amount: number;
  currency: string;
  status: string;
  card_mask?: string | null;
  description?: string | null;
  paid_at: string;
}

export interface Subscription {
  plan: string;
  plan_name: string;
  searches_limit: number;
  plan_expires_at: string | null;
  trial_ends_at: string | null;
  is_trial_active: boolean;
  liqpay_enabled?: boolean;
  next_payment_at?: string | null;
  card_mask?: string | null;
  recurring_active?: boolean;
  payments?: BillingPayment[];
}

export interface LiqPayCheckout {
  order_id: string;
  checkout_url: string;
  data: string;
  signature: string;
  amount: number;
  currency: string;
  plan: string;
  plan_name: string;
  credit_uah?: number;
  list_price_uah?: number | null;
  enable_subscribe?: boolean;
  free_upgrade?: boolean;
}

export interface UpgradeQuote {
  current_plan: string;
  current_plan_name: string;
  current_price_uah: number;
  target_plan: string;
  target_plan_name: string;
  target_price_uah: number;
  target_searches_limit: number;
  days_remaining: number;
  period_days: number;
  target_period_days: number;
  credit_uah: number;
  amount_due_uah: number;
  enable_subscribe: boolean;
  is_upgrade: boolean;
  is_free_upgrade: boolean;
  recommended: boolean;
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

export interface VinCheckRegion {
  name?: string | null;
  name_ua?: string | null;
  slug?: string | null;
  codes: string[];
}

export interface VinCheckOperation {
  registered_at?: string | null;
  is_last?: boolean | null;
  digits?: string | null;
  vendor?: string | null;
  model?: string | null;
  model_year?: number | null;
  operation_ua?: string | null;
  operation_ru?: string | null;
  operation_group_ua?: string | null;
  department?: string | null;
  color?: string | null;
  displacement?: number | null;
  address?: string | null;
  kind_ua?: string | null;
  is_registered_to_company?: boolean | null;
}

export interface VinCheckStolen {
  theft_at?: string | null;
  vendor_title?: string | null;
  color?: string | null;
  car_type?: string | null;
  chassis_number?: string | null;
  body_number?: string | null;
  department_title?: string | null;
}

export interface VinCheckResult {
  vin: string;
  plate?: string | null;
  vendor?: string | null;
  model?: string | null;
  model_year?: number | null;
  photo_url?: string | null;
  is_stolen: boolean;
  color?: string | null;
  displacement?: number | null;
  kind_ua?: string | null;
  registrations_count: number;
  first_registered_at?: string | null;
  last_registered_at?: string | null;
  region?: VinCheckRegion | null;
  operations: VinCheckOperation[];
  stolen_details: VinCheckStolen[];
  source_url: string;
  note?: string | null;
}
