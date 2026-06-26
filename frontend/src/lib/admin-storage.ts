const ADMIN_TOKEN_KEY = "autoradar_admin_token";
const ADMIN_COOKIE = "autoradar_admin_token";

export function setAdminToken(token: string) {
  localStorage.setItem(ADMIN_TOKEN_KEY, token);
  document.cookie = `${ADMIN_COOKIE}=${encodeURIComponent(token)}; path=/; max-age=${12 * 3600}; SameSite=Lax`;
}

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ADMIN_TOKEN_KEY);
}

export function clearAdminToken() {
  localStorage.removeItem(ADMIN_TOKEN_KEY);
  document.cookie = `${ADMIN_COOKIE}=; path=/; max-age=0`;
}
