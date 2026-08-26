const ALLOWED_HOSTS = new Set([
  "localhost:3000",
  "127.0.0.1:3000",
  "carbit.info",
  "www.carbit.info",
  "carbit.telebots.site",
]);

export function isAllowedGuestSearchRequest(origin: string | null, host: string | null): boolean {
  if (origin) {
    try {
      const parsed = new URL(origin);
      if (host && parsed.host === host) return true;
      return ALLOWED_HOSTS.has(parsed.host);
    } catch {
      return false;
    }
  }
  if (host && ALLOWED_HOSTS.has(host)) return true;
  return false;
}

export function isAllowedSecFetchSite(value: string | null): boolean {
  if (!value) return true;
  return value === "same-origin" || value === "same-site";
}
