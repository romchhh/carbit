const TOKEN_KEY = "autoradar_token";
const COOKIE_NAME = "autoradar_token";
const REMEMBER_ME_KEY = "autoradar_remember_me";
const SAVED_EMAIL_KEY = "autoradar_saved_email";
const REMEMBER_MAX_AGE = 30 * 24 * 60 * 60;

function writeCookie(token: string, remember: boolean) {
  const secure =
    typeof window !== "undefined" && window.location.protocol === "https:";
  const base = `${COOKIE_NAME}=${encodeURIComponent(token)}; path=/; SameSite=Lax${
    secure ? "; Secure" : ""
  }`;
  document.cookie = remember ? `${base}; max-age=${REMEMBER_MAX_AGE}` : base;
}

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

  writeCookie(token, remember);
}

function getTokenFromCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${COOKIE_NAME}=([^;]*)`));
  if (!match?.[1]) return null;
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;

  const fromStorage = localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY);
  if (fromStorage) return fromStorage;

  const fromCookie = getTokenFromCookie();
  if (!fromCookie) return null;

  localStorage.setItem(TOKEN_KEY, fromCookie);
  localStorage.setItem(REMEMBER_ME_KEY, "1");
  writeCookie(fromCookie, true);
  return fromCookie;
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
