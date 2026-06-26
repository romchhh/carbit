const TOKEN_KEY = "autoradar_token";
const COOKIE_NAME = "autoradar_token";
const REMEMBER_ME_KEY = "autoradar_remember_me";
const SAVED_EMAIL_KEY = "autoradar_saved_email";
const REMEMBER_MAX_AGE = 7 * 24 * 60 * 60;

function writeCookie(token: string, remember: boolean) {
  const base = `${COOKIE_NAME}=${encodeURIComponent(token)}; path=/; SameSite=Lax`;
  document.cookie = remember ? `${base}; max-age=${REMEMBER_MAX_AGE}` : base;
}

export function setToken(token: string, remember = true) {
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);

  if (remember) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    sessionStorage.setItem(TOKEN_KEY, token);
  }

  writeCookie(token, remember);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  document.cookie = `${COOKIE_NAME}=; path=/; max-age=0`;
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
