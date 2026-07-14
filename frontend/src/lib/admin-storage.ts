const ADMIN_TOKEN_KEY = "autoradar_admin_token";

/** JS copy for Bearer. HttpOnly cookie знімається лише через POST /admin/auth/logout. */

export function setAdminToken(token: string) {
  localStorage.setItem(ADMIN_TOKEN_KEY, token);
}

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ADMIN_TOKEN_KEY);
}

export function clearAdminToken() {
  localStorage.removeItem(ADMIN_TOKEN_KEY);
}
