const TOKEN_KEY = "autoradar_token";
const REMEMBER_ME_KEY = "autoradar_remember_me";
const SAVED_EMAIL_KEY = "autoradar_saved_email";

/** Auth cookie is HttpOnly (set by API). JS only keeps a copy for Bearer headers. */

export function setToken(token: string, remember = true) {
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);

  if (remember) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(REMEMBER_ME_KEY, "1");
  } else {
    sessionStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(REMEMBER_ME_KEY, "0");
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  // Best-effort clear of legacy non-HttpOnly cookie if present
  document.cookie = "autoradar_token=; path=/; max-age=0";
}

export function saveLoginCredentials(email: string, remember: boolean) {
  localStorage.setItem(REMEMBER_ME_KEY, remember ? "1" : "0");
  if (remember) {
    localStorage.setItem(SAVED_EMAIL_KEY, email);
  } else {
    localStorage.removeItem(SAVED_EMAIL_KEY);
  }
}

export function getSavedEmail(): string {
  return localStorage.getItem(SAVED_EMAIL_KEY) ?? "";
}

export function getRememberMePreference(): boolean {
  return localStorage.getItem(REMEMBER_ME_KEY) !== "0";
}
