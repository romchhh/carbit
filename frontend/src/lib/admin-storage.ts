const ADMIN_TOKEN_KEY = "autoradar_admin_token";

/** Admin cookie is HttpOnly (set by API). */

export function setAdminToken(token: string) {
  localStorage.setItem(ADMIN_TOKEN_KEY, token);
}

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ADMIN_TOKEN_KEY);
}

export function clearAdminToken() {
  localStorage.removeItem(ADMIN_TOKEN_KEY);
  document.cookie = "autoradar_admin_token=; path=/; max-age=0";
}
